import json
from typing import Annotated, NewType

from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.model.campaign_config import CampaignID
from eligibility_signposting_api.model.consumer_mapping import ConsumerMapping, ConsumerId

BucketName = NewType("BucketName", str)


@service
class ConsumerMappingRepo:
    """Repository class for Campaign Rules, which we can use to calculate a person's eligibility for vaccination.

    These rules are stored as JSON files in AWS S3."""

    def __init__(
        self,
        s3_client: Annotated[BaseClient, Inject(qualifier="s3")],
        bucket_name: Annotated[BucketName, Inject(param="consumer_mapping_bucket_name")],
    ) -> None:
        super().__init__()
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def get_permitted_campaign_ids(self, consumer_id: ConsumerId) -> list[CampaignID] | None:
        consumer_mappings = self.s3_client.list_objects(Bucket=self.bucket_name)["Contents"][0]
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=f"{consumer_mappings['Key']}")
        body = response["Body"].read()
        return ConsumerMapping.model_validate(json.loads(body)).get(consumer_id)
