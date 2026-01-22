import json
from typing import Annotated, NewType

from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.model.campaign_config import CampaignID
from eligibility_signposting_api.model.consumer_mapping import ConsumerId, ConsumerMapping

BucketName = NewType("BucketName", str)


@service
class ConsumerMappingRepo:
    """Repository class for Consumer Mapping"""

    def __init__(
        self,
        s3_client: Annotated[BaseClient, Inject(qualifier="s3")],
        bucket_name: Annotated[BucketName, Inject(param="consumer_mapping_bucket_name")],
    ) -> None:
        super().__init__()
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def get_permitted_campaign_ids(self, consumer_id: ConsumerId) -> list[CampaignID] | None:
        objects = self.s3_client.list_objects(Bucket=self.bucket_name).get("Contents")

        if not objects:
            return None

        consumer_mappings_obj = objects[0]
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=consumer_mappings_obj["Key"])
        body = response["Body"].read()

        mapping_result = ConsumerMapping.model_validate(json.loads(body)).get(consumer_id)

        if mapping_result is None:
            return None

        return [item.campaign for item in mapping_result]
