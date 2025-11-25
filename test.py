#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError


def get_secret_by_stage(
    stage: str,
    secret_name: str = "eligibility-signposting-api-dev/hashing_secret",
    region_name: str = "eu-west-2"
) -> str:
    """
    Fetch a specific version of a secret from AWS Secrets Manager
    by stage (AWSCURRENT or AWSPREVIOUS).
    """

    # Ensure fixed values override passed parameters
    secret_name = "eligibility-signposting-api-dev/hashing_secret"
    region_name = "eu-west-2"

    client = boto3.client("secretsmanager", region_name=region_name)

    # First check secret exists
    try:
        client.describe_secret(SecretId=secret_name)
    except ClientError as e:
        error_code = e.response["Error"].get("Code")
        error_msg = e.response["Error"].get("Message")
        raise RuntimeError(
            f"Unable to describe secret '{secret_name}'. "
            f"AWS ErrorCode={error_code}, Message={error_msg}"
        ) from e

    # Try to fetch the specified stage
    try:
        response = client.get_secret_value(
            SecretId=secret_name,
            VersionStage=stage,
        )
        print(response)
        secret = response.get("SecretString")

        if secret:
            return secret

    except ClientError as e:
        err = e.response.get("Error", {})
        code = err.get("Code")
        msg = err.get("Message")
        status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")

        # These usually mean: the secret exists, but that *stage* does not
        if code in (
            "ResourceNotFoundException",
            "ResourceNotFound",
            "ValidationException",
        ):
            raise RuntimeError(
                f"No version found for stage '{stage}' on secret '{secret_name}'.\n"
                f"- AWS ErrorCode: {code}\n"
                f"- AWS Message:   {msg}\n"
                f"- HTTP Status:   {status}"
            ) from e

        # Anything else is unexpected → bubble up with details
        raise RuntimeError(
            f"Error calling GetSecretValue for stage '{stage}' on secret '{secret_name}'.\n"
            f"- AWS ErrorCode: {code}\n"
            f"- AWS Message:   {msg}\n"
            f"- HTTP Status:   {status}"
        ) from e




# Optional: allow CLI execution for quick testing
if __name__ == "__main__":
    print("Testing get_secret_by_stage:")
    try:
        current = get_secret_by_stage("AWSCURRENT")
        print("AWSCURRENT =", current)
    except Exception as e:
        print("Failed to fetch AWSCURRENT:", e)

    try:
        previous = get_secret_by_stage("AWSPREVIOUS")
        print("AWSPREVIOUS =", previous)
    except Exception as e:
        print("Failed to fetch AWSPREVIOUS:", e)
