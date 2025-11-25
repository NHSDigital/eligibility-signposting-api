from wireup import service
import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from wireup import Inject, service
from typing import Annotated

from boto3 import Session

# @service(qualifier="nhs_hmac_key")
# def nhs_hmac_key_factory() -> bytes: # -> dict[str, bytes]:
#     # return b"abc123"
#     keys: dict[str, bytes] = {}
#     #return keys
#
#     # return {
#     # "AWSCURRENT": b"current_dummy_key",
#     # "AWSPREVIOUS": b"previous_dummy_key"
#     # }
#
#     for stage in ("AWSCURRENT", "AWSPREVIOUS"):
#         value = get_secret_by_stage()
#         if value:
#             keys[stage] = value.encode("utf-8")
#
#     # if keys = {}, then raise error
#     if not keys:
#         raise RuntimeError("No valid NHS HMAC secret keys available")
#
#     return keys

@service(qualifier="secretsmanager")
def secretsmanager_client_factory(session: Session) -> BaseClient:
    return session.client("secretsmanager")


@service(qualifier="nhs_hmac_key")
def nhs_hmac_key_factory(
    secrets_client: Annotated[BaseClient, Inject(qualifier="secretsmanager")],
) -> bytes:
    keys: dict[str, bytes] = {}

    for stage in ("AWSCURRENT", "AWSPREVIOUS"):
        value = get_secret_by_stage(secrets_client)
        if value:
            keys[stage] = value.encode("utf-8")

    if not keys:
        raise RuntimeError("No valid NHS HMAC secret keys available")

    return keys


def get_secret_by_stage(secrets_client: BaseClient
                        #secrets_client: Annotated[BaseClient, Inject(qualifier="secretsmanager")],
                        ) -> str:
    secret_name = "eligibility-signposting-api-dev/hashing_secret"
    region_name = "eu-west-2"
    # client = boto3.client("secretsmanager", region_name=region_name)
    stage="AWSCURRENT"
    try:
        secrets_client.describe_secret(SecretId=secret_name)
    except ClientError as e:
        raise RuntimeError(f"Secret '{secret_name}' does not exist") from e

    version_stages = ["AWSCURRENT", "AWSPREVIOUS"]  # add "AWSPENDING" later

    #for stage in version_stages:
    try:
        response = secrets_client.get_secret_value(
            SecretId=secret_name,
            VersionStage=stage
        )
        secret = response.get("SecretString") # response.get("SecretBinary")
        if secret:
            return secret
    # except ClientError as e:
    #     raise e # Needs expanding as it would raise after 1 iteration currently

    except ClientError as e:
        if e.response["Error"]["Code"] not in (
            "ResourceNotFoundException",
            "ResourceNotFound",
            "ValidationException",
        ):
            raise e

    raise RuntimeError(f"No valid version found for secret '{secret_name}'")


