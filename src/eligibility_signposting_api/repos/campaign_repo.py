import json
import logging
import os
import time
from collections.abc import Generator
from typing import Annotated, NewType

from aws_xray_sdk.core import xray_recorder
from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.model.campaign_config import CampaignConfig, Rules
from eligibility_signposting_api.config.constants import ttl

BucketName = NewType("BucketName", str)

logger = logging.getLogger(__name__)

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
        self._campaign_configs_cache: list[CampaignConfig] | None = None
        self._cache_expiry_epoch: float = 0.0
        self._cache_ttl_seconds: int = int(ttl.get(os.getenv("ENVIRONMENT"), 0))

    def get_campaign_configs(self, bypass_cache: bool = False) -> Generator[CampaignConfig, None, None]:
        now = time.time()
        cache_enabled = self._cache_ttl_seconds > 0
        cache_valid = (
            cache_enabled
            and not bypass_cache
            and self._campaign_configs_cache is not None
            and now < self._cache_expiry_epoch
        )

        with xray_recorder.in_subsegment("CampaignRepo.get_campaign_configs"):
            if cache_valid:
                logger.info("Using cached campaign configs")
                yield from self._campaign_configs_cache
                return

            logger.info(
                "Refreshing campaign configs from S3 (bypass_cache=%s, ttl_seconds=%s)",
                bypass_cache,
                self._cache_ttl_seconds,
            )
            campaign_configs = self._load_campaign_configs_from_s3()

            if cache_enabled and not bypass_cache:
                self._campaign_configs_cache = campaign_configs
                self._cache_expiry_epoch = now + self._cache_ttl_seconds

            yield from campaign_configs

    def _load_campaign_configs_from_s3(self) -> list[CampaignConfig]:
        campaign_configs: list[CampaignConfig] = []

        with xray_recorder.in_subsegment("CampaignRepo.load_campaign_configs_from_s3"):
            with xray_recorder.in_subsegment("list_objects"):
                campaign_objects = self.s3_client.list_objects(Bucket=self.bucket_name)

            with xray_recorder.in_subsegment("get_objects"):
                for campaign_object in campaign_objects.get("Contents", []):
                    response = self.s3_client.get_object(
                        Bucket=self.bucket_name,
                        Key=f"{campaign_object['Key']}",
                    )
                    body = response["Body"].read()
                    campaign_configs.append(
                        Rules.model_validate(json.loads(body)).campaign_config
                    )

        return campaign_configs
