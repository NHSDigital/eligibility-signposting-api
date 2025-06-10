import logging
import os
from collections.abc import Sequence
from functools import cache
from typing import Any, NewType

from pythonjsonlogger.json import JsonFormatter
from yarl import URL

from eligibility_signposting_api.repos.campaign_repo import BucketName
from eligibility_signposting_api.repos.person_repo import TableName

LOG_LEVEL = logging.getLevelNamesMapping().get(os.getenv("LOG_LEVEL", ""), logging.WARNING)

AwsRegion = NewType("AwsRegion", str)
AwsAccessKey = NewType("AwsAccessKey", str)
AwsSecretAccessKey = NewType("AwsSecretAccessKey", str)


@cache
def config() -> dict[str, Any]:
    person_table_name = TableName(os.getenv("PERSON_TABLE_NAME", "test_eligibility_datastore"))
    rules_bucket_name = BucketName(os.getenv("RULES_BUCKET_NAME", "test-rules-bucket"))
    aws_default_region = AwsRegion(os.getenv("AWS_DEFAULT_REGION", "eu-west-1"))
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
            "log_level": log_level,
        }

    return {
        "aws_access_key_id": AwsAccessKey(os.getenv("AWS_ACCESS_KEY_ID", "dummy_key")),
        "aws_default_region": aws_default_region,
        "aws_secret_access_key": AwsSecretAccessKey(os.getenv("AWS_SECRET_ACCESS_KEY", "dummy_secret")),
        "dynamodb_endpoint": URL(os.getenv("DYNAMODB_ENDPOINT", "http://localhost:4566")),
        "person_table_name": person_table_name,
        "s3_endpoint": URL(os.getenv("S3_ENDPOINT", "http://localhost:4566")),
        "rules_bucket_name": rules_bucket_name,
        "log_level": log_level,
    }


def init_logging(quieten: Sequence[str] = ("asyncio", "botocore", "boto3", "mangum", "urllib3")) -> None:
    log_format = "%(asctime)s %(levelname)-8s %(name)s %(module)s.py:%(funcName)s():%(lineno)d %(message)s"
    formatter = JsonFormatter(log_format)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.root.handlers = []  # Clear any existing handlers
    logging.root.setLevel(LOG_LEVEL)  # Set log level
    logging.root.addHandler(handler)  # Add handler

    for q in quieten:
        logging.getLogger(q).setLevel(logging.WARNING)
