import json
from collections.abc import Generator
from typing import Annotated, NewType

from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.model.rules import CampaignConfig, Rules

BucketName = NewType("BucketName", str)


@service
class RulesRepo:
    """Repository class for Campaign Rules, which we can use to calculate a person's eligibility for vaccination.

    These rules are stored as JSON files in AWS S3."""

    def __init__(
        self,
        s3_client: Annotated[BaseClient, Inject(qualifier="s3")],
        bucket_name: Annotated[BucketName, Inject(param="rules_bucket_name")],
    ) -> None:
        super().__init__()
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def get_campaign_configs(self) -> Generator[CampaignConfig]:
        campaign_objects = self.s3_client.list_objects(Bucket=self.bucket_name)
        for campaign_object in campaign_objects["Contents"]:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=f"{campaign_object['Key']}")
            body = response["Body"].read()
            yield Rules.model_validate(json.loads(body)).campaign_config
