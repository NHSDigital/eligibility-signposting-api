import os
import json
from pathlib import Path
from dotenv import load_dotenv
import boto3

def before_all(context):
    print("[>] Loading .env and initializing AWS fixtures...")

    # Load environment variables
    load_dotenv(dotenv_path=".env")

    context.base_url = os.getenv("BASE_URL")
    context.api_key = os.getenv("API_KEY")
    context.valid_nhs_number = os.getenv("VALID_NHS_NUMBER", "50000000004")

    context.aws_region = os.getenv("AWS_REGION", "eu-west-2")
    context.inserted_items = []

    # AWS failure toggle
    abort_on_aws_error = os.getenv("ABORT_ON_AWS_FAILURE", "false").lower() == "true"

    # ---------- S3 configuration ----------
    context.s3_bucket = os.getenv("S3_BUCKET_NAME")
    context.s3_upload_dir = os.getenv("S3_UPLOAD_DIR", "")
    context.s3_data_path = Path(os.getenv("S3_JSON_SOURCE_DIR", "./data/s3")).resolve()

    # ---------- DynamoDB configuration ----------
    context.dynamodb_table_name = os.getenv("DYNAMODB_TABLE_NAME", "eligibilty_data_store")
    context.dynamo_data_path = Path(os.getenv("DYNAMO_JSON_SOURCE_DIR", "./data/dynamoDB/test_data.json")).resolve()

    print(f"[>] ABORT_ON_AWS_FAILURE={abort_on_aws_error}")
    print(f"[>] KEEP_SEED={os.getenv('KEEP_SEED', 'false').lower()}")

    # ---------- DynamoDB Seeding ----------
    try:
        context.dynamodb = boto3.resource("dynamodb", region_name=context.aws_region)
        context.table = context.dynamodb.Table(context.dynamodb_table_name)
        _ = context.table.table_status
        print(f"[v] Connected to DynamoDB table: {context.dynamodb_table_name}")
    except Exception as e:
        print(f"[x] DynamoDB not accessible: {e}")
        if abort_on_aws_error:
            context.abort_all = True
        return

    if not context.dynamo_data_path.exists():
        print(f"[x] Seed file not found: {context.dynamo_data_path}")
        if abort_on_aws_error:
            context.abort_all = True
        return

    try:
        with open(context.dynamo_data_path, "r") as f:
            items = json.load(f)
    except Exception as e:
        print(f"[x] Failed to load seed file: {e}")
        if abort_on_aws_error:
            context.abort_all = True
        return

    print(f"[>] Inserting {len(items)} items into DynamoDB...")
    for item in items:
        try:
            context.table.put_item(Item=item)
            context.inserted_items.append(item)
        except Exception as e:
            print(f"[x] Failed to insert item {item.get('PK', '<unknown>')}: {e}")
    print(f"[v] Inserted {len(context.inserted_items)} items")

    # ---------- S3 Upload ----------
    if context.s3_bucket:
        print(f"[>] Uploading JSON files from {context.s3_data_path} to S3 bucket: {context.s3_bucket}/{context.s3_upload_dir}")
        try:
            s3_client = boto3.client("s3", region_name=context.aws_region)
            if context.s3_data_path.exists():
                json_files = list(context.s3_data_path.glob("*.json"))
                for file_path in json_files:
                    key = f"{context.s3_upload_dir}/{file_path.name}" if context.s3_upload_dir else file_path.name
                    try:
                        s3_client.upload_file(str(file_path), context.s3_bucket, key)
                        print(f"[v] Uploaded {file_path.name} to s3://{context.s3_bucket}/{key}")
                    except Exception as e:
                        print(f"[x] Failed to upload {file_path.name}: {e}")
            else:
                print(f"[x] S3 source directory not found: {context.s3_data_path}")
        except Exception as e:
            print(f"[x] S3 upload setup failed: {e}")
            if abort_on_aws_error:
                context.abort_all = True
                return
    else:
        print("[>] Skipping S3 upload — no S3_BUCKET_NAME set.")

def before_scenario(context, scenario):
    if getattr(context, "abort_all", False):
        scenario.skip("Skipping scenario due to setup failure")

    if "requires_dynamodb" in scenario.tags and not context.inserted_items:
        scenario.skip("Skipping due to missing seeded DynamoDB data")

def after_all(context):
    # ---------- Early Exit on KEEP_SEED ----------
    if os.getenv("KEEP_SEED", "").lower() == "true":
        print("[>] KEEP_SEED=true — skipping cleanup.")
        return

    # ---------- DynamoDB Cleanup ----------
    if not context.inserted_items:
        print("[>] No items were inserted — skipping DynamoDB cleanup.")
    else:
        print("[>] Cleaning up seeded items from DynamoDB...")
        delete_count = 0
        for item in context.inserted_items:
            nhs_number = item.get("NHS_NUMBER")
            attribute_type = item.get("ATTRIBUTE_TYPE")

            if nhs_number and attribute_type:
                try:
                    context.table.delete_item(Key={
                        "NHS_NUMBER": nhs_number,
                        "ATTRIBUTE_TYPE": attribute_type
                    })
                    delete_count += 1
                except Exception as e:
                    print(f"[x] Failed to delete item ({nhs_number}, {attribute_type}): {e}")
            else:
                print(f"[x] Cannot delete item — missing NHS_NUMBER or ATTRIBUTE_TYPE: {item}")
        print(f"[v] Deleted {delete_count}/{len(context.inserted_items)} DynamoDB items")

    # ---------- S3 Cleanup ----------
    if context.s3_bucket and context.s3_data_path.exists():
        print("[>] Cleaning up uploaded files from S3...")
        try:
            s3_client = boto3.client("s3", region_name=context.aws_region)
            json_files = list(context.s3_data_path.glob("*.json"))
            deleted_files = 0
            for file_path in json_files:
                key = f"{context.s3_upload_dir}/{file_path.name}" if context.s3_upload_dir else file_path.name
                try:
                    s3_client.delete_object(Bucket=context.s3_bucket, Key=key)
                    print(f"[v] Deleted s3://{context.s3_bucket}/{key}")
                    deleted_files += 1
                except Exception as e:
                    print(f"[x] Failed to delete s3://{context.s3_bucket}/{key}: {e}")
            print(f"[v] Deleted {deleted_files}/{len(json_files)} files from S3")
        except Exception as e:
            print(f"[x] S3 cleanup failed: {e}")
    else:
        print("[>] Skipping S3 cleanup — no bucket or source directory not found.")
