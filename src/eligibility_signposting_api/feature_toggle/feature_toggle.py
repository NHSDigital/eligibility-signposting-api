import logging
import os

import boto3
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached

aws_region = os.getenv("AWS_DEFAULT_REGION")
ssm_client = boto3.client("ssm", region_name=aws_region)
environment = os.getenv("ENV")
feature_toggles_prefix = f"/{environment}/feature_toggles/"

logger = logging.getLogger(__name__)

ssm_cache_in_seconds = TTLCache(maxsize=128, ttl=300)


@cached(ssm_cache_in_seconds)
def get_ssm_parameter(parameter_name: str) -> str:
    logger.info("Fetching '%s' from AWS SSM (not from cache).", parameter_name)
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        logger.warning("Parameter '%s' not found in SSM.", parameter_name)
        return "false"
    except ClientError:
        logger.exception("An AWS client error occurred fetching '%s' from SSM.", parameter_name)
        return "false"


def is_feature_enabled(feature_name: str) -> bool:
    parameter_name = feature_toggles_prefix + feature_name
    return get_ssm_parameter(parameter_name).lower().strip() == "true"
