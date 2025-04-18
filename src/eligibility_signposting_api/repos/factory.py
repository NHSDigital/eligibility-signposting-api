import logging
from typing import Annotated

from boto3 import Session
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient
from wireup import Inject, service
from yarl import URL

from eligibility_signposting_api.config import AwsAccessKey, AwsRegion, AwsSecretAccessKey

logger = logging.getLogger(__name__)


@service
def boto3_session_factory(
    aws_default_region: Annotated[AwsRegion, Inject(param="aws_default_region")],
    aws_access_key_id: Annotated[AwsAccessKey, Inject(param="aws_access_key_id")],
    aws_secret_access_key: Annotated[AwsSecretAccessKey, Inject(param="aws_secret_access_key")],
) -> Session:
    return Session(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=aws_default_region
    )


@service(qualifier="dynamodb")
def dynamodb_resource_factory(
    session: Session, dynamodb_endpoint: Annotated[URL, Inject(param="dynamodb_endpoint")]
) -> ServiceResource:
    return session.resource("dynamodb", endpoint_url=str(dynamodb_endpoint))


@service(qualifier="s3")
def s3_service_factory(
    session: Session, dynamodb_endpoint: Annotated[URL, Inject(param="dynamodb_endpoint")]
) -> BaseClient:
    return session.client("s3", endpoint_url=str(dynamodb_endpoint))
