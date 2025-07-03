import json
from collections.abc import Generator

import pytest
from botocore.client import BaseClient
from hamcrest import assert_that, has_item

from eligibility_signposting_api.model.rules import CampaignConfig
from eligibility_signposting_api.repos.campaign_repo import BucketName, CampaignRepo
from tests.fixtures.builders.model.rule import CampaignConfigFactory
from tests.fixtures.matchers.rules import is_campaign_config, is_iteration, is_iteration_rule


@pytest.fixture(scope="module")
def campaign_config(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = CampaignConfigFactory.build()
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


def test_get_campaign_config(s3_client: BaseClient, rules_bucket: BucketName, campaign_config: CampaignConfig):
    # Given
    repo = CampaignRepo(s3_client, rules_bucket)

    # When
    actual = list(repo.get_campaign_configs())

    # Then
    assert_that(
        actual,
        has_item(
            is_campaign_config()
            .with_id(campaign_config.id)
            .and_name(campaign_config.name)
            .and_version(campaign_config.version)
            .and_iterations(
                has_item(
                    is_iteration()
                    .with_id(campaign_config.iterations[0].id)
                    .and_default_comms_routing(campaign_config.iterations[0].default_comms_routing)
                    .and_actions_mapper(campaign_config.iterations[0].actions_mapper)
                    .and_iteration_rules(
                        has_item(is_iteration_rule().with_name(campaign_config.iterations[0].iteration_rules[0].name))
                    )
                )
            )
        ),
    )
