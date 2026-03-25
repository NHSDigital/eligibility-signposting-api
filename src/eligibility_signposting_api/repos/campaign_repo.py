import json
import logging
from collections.abc import Generator
from typing import Annotated, NewType

from aws_xray_sdk.core import xray_recorder
from botocore.client import BaseClient
from cachetools import TTLCache
from wireup import Inject, service

from eligibility_signposting_api.config.constants import CACHE_TTL_SECONDS
from eligibility_signposting_api.model.campaign_config import CampaignConfig, Rules

BucketName = NewType("BucketName", str)

logger = logging.getLogger(__name__)

campaign_config_cache: TTLCache[str, list[CampaignConfig]] = TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS)


@service
class CampaignRepo:
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

    def get_campaign_configs(self, consumer_id: str) -> Generator[CampaignConfig]:
        bypass = "test-" in consumer_id
        cache_key = "all_campaigns"
        cached = None if bypass else campaign_config_cache.get(cache_key)

        with xray_recorder.in_subsegment("CampaignRepo.get_campaign_configs"):
            if cached is not None:
                logger.info("Using cached campaign configs")
                yield from cached
                return

            logger.info(
                "Refreshing campaign configs from S3 (consumer_id=%s, ttl_seconds=%s)",
                consumer_id,
                CACHE_TTL_SECONDS,
            )
            configs = self._load_campaign_configs_from_s3()

            if not bypass:
                campaign_config_cache[cache_key] = configs

            yield from configs

    def _load_campaign_configs_from_s3(self) -> list[CampaignConfig]:
        campaign_configs: list[CampaignConfig] = []

        with xray_recorder.in_subsegment("CampaignRepo.load_campaign_configs_from_s3"):
            with xray_recorder.in_subsegment("list_objects"):
                campaign_objects = self.s3_client.list_objects(Bucket=self.bucket_name)

            with xray_recorder.in_subsegment("get_objects"):
                for campaign_object in campaign_objects.get("Contents"):
                    response = self.s3_client.get_object(
                        Bucket=self.bucket_name,
                        Key=f"{campaign_object['Key']}",
                    )
                    body = response["Body"].read()
                    campaign_configs.append(Rules.model_validate(json.loads(body)).campaign_config)

        return campaign_configs
