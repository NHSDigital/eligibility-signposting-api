import json
import logging
from typing import Annotated, NewType

from botocore.client import BaseClient
from botocore.exceptions import ClientError
from wireup import Inject, service

from eligibility_signposting_api.config.constants import CONSUMER_MAPPING_FILE_NAME
from eligibility_signposting_api.model.campaign_config import CampaignID
from eligibility_signposting_api.model.consumer_mapping import ConsumerId, ConsumerMapping

logger = logging.getLogger(__name__)

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
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=CONSUMER_MAPPING_FILE_NAME)
            body = response["Body"].read()

            mapping_result = ConsumerMapping.model_validate(json.loads(body)).get(consumer_id)

            if mapping_result is None:
                return None

            return [item.campaign_config_id for item in mapping_result]

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            logger.exception("Error while reading consumer mapping config file : %s", CONSUMER_MAPPING_FILE_NAME)
            raise
