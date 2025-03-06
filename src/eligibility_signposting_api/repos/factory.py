import logging
from typing import Annotated

import boto3
from boto3.resources.base import ServiceResource
from wireup import Inject, service
from yarl import URL

from eligibility_signposting_api.config import AwsAccessKey, AwsRegion, AwsSecretAccessKey

logger = logging.getLogger(__name__)


@service
def dynamodb_resource_factory(
    dynamodb_endpoint: Annotated[URL, Inject(param="dynamodb_endpoint")],
    aws_region: Annotated[AwsRegion, Inject(param="aws_region")],
    aws_access_key_id: Annotated[AwsAccessKey, Inject(param="aws_access_key_id")],
    aws_secret_access_key: Annotated[AwsSecretAccessKey, Inject(param="aws_secret_access_key")],
) -> ServiceResource:
    logger.info("creating dynamodb_resource with endpoint %s, region %s", dynamodb_endpoint, aws_region)
    resource = boto3.resource(
        "dynamodb",
        endpoint_url=str(dynamodb_endpoint),
        region_name=aws_region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    logger.info("built dynamodb_resource %r", resource)
    return resource
