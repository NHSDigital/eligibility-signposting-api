import logging
import os
from functools import cache
from typing import Any, NewType

from yarl import URL

from eligibility_signposting_api.repos.campaign_repo import BucketName
from eligibility_signposting_api.repos.person_repo import TableName

LOG_LEVEL = logging.getLevelNamesMapping().get(os.getenv("LOG_LEVEL", ""), logging.WARNING)

AwsRegion = NewType("AwsRegion", str)
AwsAccessKey = NewType("AwsAccessKey", str)
AwsSecretAccessKey = NewType("AwsSecretAccessKey", str)
AwsKinesisFirehoseStreamName = NewType("AwsKinesisFirehoseStreamName", str)


@cache
def config() -> dict[str, Any]:
    person_table_name = TableName(os.getenv("PERSON_TABLE_NAME", "test_eligibility_datastore"))
    rules_bucket_name = BucketName(os.getenv("RULES_BUCKET_NAME", "test-rules-bucket"))
    audit_bucket_name = BucketName(os.getenv("AUDIT_BUCKET_NAME", "test-audit-bucket"))
    aws_default_region = AwsRegion(os.getenv("AWS_DEFAULT_REGION", "eu-west-1"))
    enable_xray_patching = bool(os.getenv("ENABLE_XRAY_PATCHING", "false"))
    kinesis_audit_stream_to_s3 = AwsKinesisFirehoseStreamName(
        os.getenv("KINESIS_AUDIT_STREAM_TO_S3", "test_kinesis_audit_stream_to_s3")
    )
    log_level = LOG_LEVEL

    if os.getenv("ENV"):
        return {
            "aws_access_key_id": None,
            "aws_default_region": aws_default_region,
            "aws_secret_access_key": None,
            "dynamodb_endpoint": None,
            "person_table_name": person_table_name,
            "s3_endpoint": None,
            "rules_bucket_name": rules_bucket_name,
            "audit_bucket_name": audit_bucket_name,
            "firehose_endpoint": None,
            "kinesis_audit_stream_to_s3": kinesis_audit_stream_to_s3,
            "enable_xray_patching": enable_xray_patching,
            "log_level": log_level,
        }

    local_stack_endpoint = "http://localhost:4566"
    return {
        "aws_access_key_id": AwsAccessKey(os.getenv("AWS_ACCESS_KEY_ID", "dummy_key")),
        "aws_default_region": aws_default_region,
        "aws_secret_access_key": AwsSecretAccessKey(os.getenv("AWS_SECRET_ACCESS_KEY", "dummy_secret")),
        "dynamodb_endpoint": URL(os.getenv("DYNAMODB_ENDPOINT", local_stack_endpoint)),
        "person_table_name": person_table_name,
        "s3_endpoint": URL(os.getenv("S3_ENDPOINT", local_stack_endpoint)),
        "rules_bucket_name": rules_bucket_name,
        "audit_bucket_name": audit_bucket_name,
        "firehose_endpoint": URL(os.getenv("FIREHOSE_ENDPOINT", local_stack_endpoint)),
        "kinesis_audit_stream_to_s3": kinesis_audit_stream_to_s3,
        "enable_xray_patching": enable_xray_patching,
        "log_level": log_level,
    }
