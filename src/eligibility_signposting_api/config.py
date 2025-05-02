import logging
import os
from collections.abc import Sequence
from functools import lru_cache
from typing import Any, NewType

from pythonjsonlogger.json import JsonFormatter
from yarl import URL

from eligibility_signposting_api.repos.eligibility_repo import TableName
from eligibility_signposting_api.repos.rules_repo import BucketName

LOG_LEVEL = logging.getLevelNamesMapping().get(os.getenv("LOG_LEVEL", ""), logging.WARNING)

AwsRegion = NewType("AwsRegion", str)
AwsAccessKey = NewType("AwsAccessKey", str)
AwsSecretAccessKey = NewType("AwsSecretAccessKey", str)


@lru_cache
def config() -> dict[str, Any]:
    return {
        "aws_access_key_id": AwsAccessKey(os.getenv("AWS_ACCESS_KEY_ID", "dummy_key")),
        "aws_default_region": AwsRegion(os.getenv("AWS_DEFAULT_REGION", "eu-west-1")),
        "aws_secret_access_key": AwsSecretAccessKey(os.getenv("AWS_SECRET_ACCESS_KEY", "dummy_secret")),
        "dynamodb_endpoint": URL(os.getenv("DYNAMODB_ENDPOINT", "http://localhost:4566")),
        "eligibility_table_name": TableName(os.getenv("ELIGIBILITY_TABLE_NAME", "test_eligibility_datastore")),
        "log_level": LOG_LEVEL,
        "rules_bucket_name": BucketName(os.getenv("RULES_BUCKET_NAME", "test-rules-bucket")),
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
