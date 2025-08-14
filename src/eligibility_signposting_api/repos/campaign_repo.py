import json
import logging
import os
from collections.abc import Generator
from typing import Annotated, NewType

from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.common.cache_manager import (
    CAMPAIGN_CONFIGS_CACHE_KEY,
    clear_cache,
    get_cache,
    set_cache,
)
from eligibility_signposting_api.model.campaign_config import CampaignConfig, Rules

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

    def get_campaign_configs(self) -> Generator[CampaignConfig]:
        """Get campaign configurations, using cached data if available.

        Campaign rules are loaded once per Lambda container and cached globally
        to improve performance by avoiding repeated S3 reads, unless caching is disabled for testing.
        """
        # Check if caching is disabled for tests
        if os.getenv("DISABLE_CAMPAIGN_CACHE", "").lower() in ("true", "1", "yes"):
            logger.debug("Campaign caching disabled for testing")
            yield from self._load_campaign_configs_from_s3()
            return

        cached_configs = get_cache(CAMPAIGN_CONFIGS_CACHE_KEY)

        if cached_configs is None:
            logger.info("Loading campaign configurations from S3 and caching for container reuse")
            configs = self._load_campaign_configs_from_s3()
            set_cache(CAMPAIGN_CONFIGS_CACHE_KEY, configs)
            logger.info("Cached campaign configurations", extra={"campaign_count": len(configs)})
            yield from configs
        else:
            logger.debug("Using cached campaign configurations")
            yield from cached_configs  # type: ignore[misc]

    def _load_campaign_configs_from_s3(self) -> list[CampaignConfig]:
        """Load campaign configurations from S3."""
        configs = []
        campaign_objects = self.s3_client.list_objects(Bucket=self.bucket_name)

        for campaign_object in campaign_objects["Contents"]:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=f"{campaign_object['Key']}")
            body = response["Body"].read()
            config = Rules.model_validate(json.loads(body)).campaign_config
            configs.append(config)

        return configs

    def clear_campaign_cache(self) -> None:
        """Clear the campaign configurations cache.

        This forces the next call to get_campaign_configs() to reload from S3.
        Useful for testing or when you need to refresh the data.
        """
        clear_cache(CAMPAIGN_CONFIGS_CACHE_KEY)
        logger.info("Campaign configurations cache cleared")
