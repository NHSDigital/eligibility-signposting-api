import json
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from scripts.manual_uploads.manual_s3_dynamo_upload import map_dynamo_type, run_upload


@pytest.fixture
def test_data_dir(tmp_path):
    data = [
        {
            "NHS_NUMBER": "1234567890",
            "ATTRIBUTE_TYPE": "COHORTS",
            "COHORT_MEMBERSHIPS": [{"COHORT_LABEL": "under_75", "DATE_JOINED": "2025-01-01"}],
        },
        {
            "NHS_NUMBER": "2345678901",
            "ATTRIBUTE_TYPE": "COHORTS",
            "COHORT_MEMBERSHIPS": [{"COHORT_LABEL": "over_75", "DATE_JOINED": "2025-01-01"}],
        },
        {
            "NHS_NUMBER": "3456789012",
            "ATTRIBUTE_TYPE": "COHORTS",
            "COHORT_MEMBERSHIPS": [{"COHORT_LABEL": "16+_covid", "DATE_JOINED": "2025-01-01"}],
        },
    ]
    file_path = tmp_path / "test.json"
    with Path.open(file_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    return tmp_path, data


@mock_aws
def test_script_cli_end_to_end(test_data_dir):
    # Arrange
    data_dir, expected_data = test_data_dir
    env = "test"
    region = "eu-west-2"
    s3_bucket = f"api-{env}-rules"
    dynamo_table = f"api-{env}-datastore"

    s3 = boto3.client("s3", region_name=region)
    s3.create_bucket(Bucket=s3_bucket, CreateBucketConfiguration={"LocationConstraint": region})

    dynamodb = boto3.client("dynamodb", region_name=region)
    dynamodb.create_table(
        TableName=dynamo_table,
        KeySchema=[
            {"AttributeName": "NHS_NUMBER", "KeyType": "HASH"},
            {"AttributeName": "ATTRIBUTE_TYPE", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "NHS_NUMBER", "AttributeType": "S"},
            {"AttributeName": "ATTRIBUTE_TYPE", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Act
    run_upload(
        [
            "--env",
            env,
            "--upload-s3",
            str(data_dir),
            "--upload-dynamo",
            str(data_dir),
            "--region",
            region,
            "--s3-bucket",
            s3_bucket,
            "--dynamo-table",
            dynamo_table,
        ]
    )

    key = "manual-uploads/test.json"
    obj = s3.get_object(Bucket=s3_bucket, Key=key)
    body = obj["Body"].read().decode("utf-8")
    uploaded_s3_data = [json.loads(line) for line in body.splitlines() if line.strip()]

    dynamo_items = []
    for expected_item in expected_data:
        key = {
            "NHS_NUMBER": {"S": expected_item["NHS_NUMBER"]},
            "ATTRIBUTE_TYPE": {"S": expected_item["ATTRIBUTE_TYPE"]},
        }
        response = dynamodb.get_item(TableName=dynamo_table, Key=key)
        item = response.get("Item")
        dynamo_items.append(item)

    expected_dynamo_items = [{k: map_dynamo_type(v) for k, v in item.items()} for item in expected_data]

    # Assert
    assert uploaded_s3_data == expected_data
    assert dynamo_items == expected_dynamo_items
