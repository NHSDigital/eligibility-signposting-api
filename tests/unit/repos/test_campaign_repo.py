import io
import json
from unittest.mock import MagicMock

import pytest

from eligibility_signposting_api.repos.campaign_repo import CampaignRepo, BucketName
from tests.fixtures.builders.model.rule import CampaignConfigFactory


def make_s3_body(payload: dict):
    return {"Body": io.BytesIO(json.dumps(payload).encode("utf-8"))}


class TestCampaignRepo:
    @pytest.fixture
    def mock_s3_client(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_s3_client):
        return CampaignRepo(
            s3_client=mock_s3_client,
            bucket_name=BucketName("test-bucket"),
        )

    @pytest.fixture
    def rules_payload(self):
        campaign_config = CampaignConfigFactory.build()
        return {
            "campaign_config": campaign_config.model_dump(mode="json")
        }

    def test_get_campaign_configs_loads_from_s3(self, repo, mock_s3_client, rules_payload):
        mock_s3_client.list_objects.return_value = {
            "Contents": [{"Key": "rsv.json"}]
        }
        mock_s3_client.get_object.return_value = make_s3_body(rules_payload)

        result = list(repo.get_campaign_configs("consumer_id"))

        assert len(result) == 1
        assert result[0].id == rules_payload["campaign_config"]["id"]

        mock_s3_client.list_objects.assert_called_once_with(Bucket="test-bucket")
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="rsv.json",
        )

    def test_get_campaign_configs_uses_cache_within_ttl(
        self,
        repo,
        mock_s3_client,
        monkeypatch,
    ):
        repo._cache_ttl_seconds = 60

        first_config = CampaignConfigFactory.build(version=1)

        mock_s3_client.list_objects.return_value = {
            "Contents": [{"Key": "rsv.json"}]
        }
        mock_s3_client.get_object.return_value = make_s3_body(
            {"campaign_config": first_config.model_dump(mode="json")}
        )

        monkeypatch.setattr("time.time", lambda: 1000.0)

        first = list(repo.get_campaign_configs("consumer_id"))
        second = list(repo.get_campaign_configs("consumer_id"))

        assert first[0].version == 1
        assert second[0].version == 1
        assert mock_s3_client.list_objects.call_count == 1
        assert mock_s3_client.get_object.call_count == 1

    def test_get_campaign_configs_refreshes_after_ttl_expiry(
        self,
        repo,
        mock_s3_client,
        monkeypatch,
    ):
        repo._cache_ttl_seconds = 60

        first_config = CampaignConfigFactory.build(version=1)
        second_config = CampaignConfigFactory.build(version=2)

        mock_s3_client.list_objects.return_value = {
            "Contents": [{"Key": "rsv.json"}]
        }
        mock_s3_client.get_object.side_effect = [
            make_s3_body({"campaign_config": first_config.model_dump(mode="json")}),
            make_s3_body({"campaign_config": second_config.model_dump(mode="json")}),
        ]

        current_time = {"value": 1000.0}
        monkeypatch.setattr("time.time", lambda: current_time["value"])

        first = list(repo.get_campaign_configs("consumer_id"))
        current_time["value"] = 1030.0
        second = list(repo.get_campaign_configs("consumer_id"))
        current_time["value"] = 1061.0
        third = list(repo.get_campaign_configs("test-consumer-1"))

        assert first[0].version == 1
        assert second[0].version == 1
        assert third[0].version == 2
        assert mock_s3_client.list_objects.call_count == 2
        assert mock_s3_client.get_object.call_count == 2
