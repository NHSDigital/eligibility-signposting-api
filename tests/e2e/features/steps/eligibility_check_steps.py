import logging
import os
from pathlib import Path
import json
import boto3
import requests
import copy
from behave import given, then, when
from botocore.exceptions import ClientError
from helpers.dynamodb_data_generator import DateVariableResolver, JsonTestDataProcessor
from helpers.dynamodb_data_uploader import DynamoDBDataUploader
from difflib import unified_diff

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# API endpoints
API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://" + "test" + ".eligibility-signposting-api.nhs.uk"
)

# SSM Parameter paths
SSM_BASE_PATH = "/" + "test" + "/mtls"
CERT_PARAMS = {
    "private_key": f"{SSM_BASE_PATH}/api_private_key_cert",
    "client_cert": f"{SSM_BASE_PATH}/api_client_cert",
    "ca_cert": f"{SSM_BASE_PATH}/api_ca_cert",
}


def remove_ignored_properties(obj):
    """
    Recursively remove specified properties from JSON objects before comparison.
    Creates deep copies to avoid modifying original data.

    Properties to remove:
    - meta (and all its sub-properties)
    - responseId

    Args:
        obj: The JSON object (dict, list, or primitive) to process

    Returns:
        A deep copy of the object with specified properties removed
    """
    if isinstance(obj, dict):
        # Create a new dict excluding the ignored properties
        filtered_dict = {}
        for key, value in obj.items():
            if key not in ["meta", "responseId"]:
                filtered_dict[key] = remove_ignored_properties(value)
        return filtered_dict
    elif isinstance(obj, list):
        # Recursively process each item in the list
        return [remove_ignored_properties(item) for item in obj]
    else:
        # Return primitive values as-is
        return obj


@given("AWS credentials are loaded from the environment")
def step_impl_load_aws_credentials(context):
    """Load AWS credentials from environment variables."""
    context.aws_region = os.getenv("AWS_REGION", "eu-west-2")
    context.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    context.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    context.aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    context.dynamodb_table_name = os.getenv(
        "DYNAMODB_TABLE_NAME", "eligibilty_data_store"
    )

    missing = []
    if not context.aws_region:
        missing.append("AWS_REGION")
    if not context.aws_access_key_id:
        missing.append("AWS_ACCESS_KEY_ID")
    if not context.aws_secret_access_key:
        missing.append("AWS_SECRET_ACCESS_KEY")

    assert not missing, f"Missing required environment variables: {', '.join(missing)}"

    logger.info("AWS credentials loaded successfully")


@given("mTLS certificates are downloaded and available in the out/ directory")
def step_impl_download_certificates(context):
    """Retrieve mTLS certs from SSM and write them to local files."""

    cert_dir = Path("./data/out")
    cert_dir.mkdir(parents=True, exist_ok=True)

    ssm = boto3.client(
        "ssm",
        region_name=context.aws_region,
        aws_access_key_id=context.aws_access_key_id,
        aws_secret_access_key=context.aws_secret_access_key,
        aws_session_token=context.aws_session_token,
    )

    context.cert_paths = {}
    for cert_type, param_name in CERT_PARAMS.items():
        cert_path = cert_dir / f"{cert_type}.pem"
        try:
            logger.info("Retrieving SSM parameter: %s", param_name)
            response = ssm.get_parameter(Name=param_name, WithDecryption=True)
            with cert_path.open("w") as f:
                f.write(response["Parameter"]["Value"])
            context.cert_paths[cert_type] = str(cert_path)
        except ClientError as e:
            msg = f"Failed to retrieve parameter {param_name}: {e}"
            raise RuntimeError(msg) from e

    logger.info("mTLS certificates written to local files")


@given("I generate the test data files")
def step_impl_generate_data(context):
    """Generate test data files with resolved <<DATE_...>> placeholders - once per feature."""
    if getattr(context, "feature_data_setup_done", False):
        logger.info(
            "Test data already generated for this feature, skipping generation..."
        )
        return

    logger.info("Generating test data files for feature...")
    input_dir = Path("data/in/dynamoDB").resolve()
    output_dir = Path("data/out/dynamoDB").resolve()

    resolver = DateVariableResolver()
    processor = JsonTestDataProcessor(input_dir, output_dir, resolver)

    if not input_dir.exists():
        logger.error("Input directory does not exist: %s", input_dir)
        return

    logger.info("Scanning for JSON files in directory: %s", input_dir)
    count = 0
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".json"):
                full_path = Path(root) / file
                processor.process_file(full_path)
                count += 1

    if count == 0:
        logger.warning("No .json files found in %s", input_dir)
    else:
        logger.info("Processed %d test data file(s) for feature.", count)


@given("I upload the test data files to DynamoDB")
def step_impl_upload_data(context):
    """Upload generated test data to DynamoDB - once per feature."""
    if getattr(context, "feature_data_setup_done", False):
        logger.info("Test data already uploaded for this feature, skipping upload...")
        return

    logger.info("Uploading test data to DynamoDB for feature...")
    uploader = DynamoDBDataUploader(
        aws_region=context.aws_region,
        access_key=context.aws_access_key_id,
        secret_key=context.aws_secret_access_key,
        session_token=context.aws_session_token,
    )
    inserted = uploader.upload_files_from_path(
        table_name=context.dynamodb_table_name, path=Path("data/out/dynamoDB")
    )
    assert inserted > 0, "No data uploaded to DynamoDB"

    # Store for feature-level cleanup
    context.feature_uploader = uploader
    context.feature_dynamodb_items_count = inserted
    context.feature_data_setup_done = True

    logger.info("Uploaded %d items to DynamoDB (feature-level)", inserted)


@given('I have the NHS number "{nhs_number}"')
def step_impl_nhs_number(context, nhs_number):
    context.nhs_number = nhs_number


@then("I clean up DynamoDB test data")
def step_impl_cleanup_dynamo(context):
    """Clean up DynamoDB test data - handled at feature level now."""
    logger.info(
        "DynamoDB cleanup will be handled at feature level - skipping scenario-level cleanup"
    )
    # This step becomes a no-op since cleanup is handled in after_feature hook


@when("I query the eligibility API")
def step_impl_call_eligibility_api(context):
    """Make mTLS call to Eligibility API using local certs and context NHS number."""
    if not hasattr(context, "nhs_number"):
        msg = "NHS number not set in context."
        raise AssertionError(msg)

    if not hasattr(context, "cert_paths"):
        msg = "mTLS certificate paths not present in context."
        raise AssertionError(msg)

    api_url = f"{API_BASE_URL}/patient-check/{context.nhs_number}"
    cert = (context.cert_paths["client_cert"], context.cert_paths["private_key"])
    verify = False
    headers = {"nhs-login-nhs-number": context.nhs_number}

    logger.info("Querying Eligibility API at %s", api_url)
    try:
        response = requests.get(
            api_url, cert=cert, verify=verify, timeout=30, headers=headers
        )
        context.response = response
        logger.info(
            "Querying Eligibility API response %s - %d",
            response.apparent_encoding,
            response.status_code,
        )
    except requests.exceptions.RequestException as e:
        msg = f"API request failed: {e}"
        raise RuntimeError(msg) from e


@then("the response status code should be {status_code:d}")
def step_impl_check_status_code(context, status_code):
    """Assert response HTTP status code."""
    if not hasattr(context, "response"):
        msg = "No HTTP response in context."
        raise AssertionError(msg)
    actual = context.response.status_code
    assert actual == status_code, f"Expected status {status_code}, got {actual}"


@then("the response should be valid JSON")
def step_impl_validate_json(context):
    """Assert that response content is valid JSON."""
    if not hasattr(context, "response"):
        msg = "No HTTP response in context."
        raise AssertionError(msg)

    try:
        context.json_response = context.response.json()
    except ValueError as e:
        msg = f"Response is not valid JSON: {e}"
        raise AssertionError(msg) from e


@then('the response should be matching the JSON "{json_response}"')
def step_impl_match_json_response(context, json_response):
    """
    Assert that the API response matches the expected JSON file.
    """
    expected_path = os.path.join(
        Path(__file__).parent.parent.parent, "data", "responses", json_response
    )
    if not os.path.isfile(expected_path):
        raise AssertionError(f"Expected JSON file not found: {expected_path}")

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    try:
        actual = context.response.json()
        print(f"📄 Actual JSON structure: ", actual)
    except Exception as e:
        raise AssertionError(f"Failed to parse API response as JSON: {e}")

    filtered_expected = remove_ignored_properties(expected)
    filtered_actual = remove_ignored_properties(actual)

    if filtered_expected != filtered_actual:
        expected_str = json.dumps(filtered_expected, indent=2, sort_keys=True)
        actual_str = json.dumps(filtered_actual, indent=2, sort_keys=True)
        diff = "\n".join(
            unified_diff(
                expected_str.splitlines(),
                actual_str.splitlines(),
                fromfile="expected",
                tofile="actual",
                lineterm="",
            )
        )
        raise AssertionError(f"Response JSON does not match expected.\nDiff:\n{diff}")
