"""Unit tests for campaign repository caching functionality."""

import json
from unittest.mock import MagicMock, Mock

from eligibility_signposting_api.common.cache_manager import clear_all_caches
from eligibility_signposting_api.model.campaign_config import CampaignConfig
from eligibility_signposting_api.repos.campaign_repo import BucketName, CampaignRepo
from tests.fixtures.builders.model.rule import CampaignConfigFactory


class TestCampaignRepoUnitTests:
    """Unit tests for CampaignRepo focusing on caching logic."""

    def setup_method(self):
        """Set up test environment before each test."""
        clear_all_caches()

    def test_get_campaign_configs_cache_miss_loads_from_s3(self):
        """Test that when cache is empty, configurations are loaded from S3 and cached."""
        # Given
        mock_s3_client = Mock()
        bucket_name = BucketName("test-bucket")

        # Mock S3 response for list_objects
        mock_campaign_data = CampaignConfigFactory.build()
        campaign_json = {"CampaignConfig": mock_campaign_data.model_dump(by_alias=True)}

        mock_s3_client.list_objects.return_value = {"Contents": [{"Key": "campaign1.json"}]}

        # Mock S3 response for get_object
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(campaign_json).encode()
        mock_s3_client.get_object.return_value = {"Body": mock_response}

        repo = CampaignRepo(mock_s3_client, bucket_name)

        # When
        configs = list(repo.get_campaign_configs())

        # Then
        assert len(configs) == 1
        assert isinstance(configs[0], CampaignConfig)
        assert configs[0].id == mock_campaign_data.id

        # Verify S3 was called
        mock_s3_client.list_objects.assert_called_once_with(Bucket=bucket_name)
        mock_s3_client.get_object.assert_called_once_with(Bucket=bucket_name, Key="campaign1.json")

    def test_get_campaign_configs_cache_hit_uses_cached_data(self):
        """Test that when cache contains data, it's used instead of loading from S3."""
        # Given
        mock_s3_client = Mock()
        bucket_name = BucketName("test-bucket")
        repo = CampaignRepo(mock_s3_client, bucket_name)

        # Load data first to populate cache
        mock_campaign_data = CampaignConfigFactory.build()
        campaign_json = {"CampaignConfig": mock_campaign_data.model_dump(by_alias=True)}

        mock_s3_client.list_objects.return_value = {"Contents": [{"Key": "campaign1.json"}]}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(campaign_json).encode()
        mock_s3_client.get_object.return_value = {"Body": mock_response}

        # First call to populate cache
        first_configs = list(repo.get_campaign_configs())

        # Reset mock to verify second call doesn't hit S3
        mock_s3_client.reset_mock()

        # When - second call should use cache
        second_configs = list(repo.get_campaign_configs())

        # Then
        assert len(second_configs) == 1
        assert second_configs[0].id == first_configs[0].id

        # Verify S3 was NOT called on second request
        mock_s3_client.list_objects.assert_not_called()
        mock_s3_client.get_object.assert_not_called()

    def test_get_campaign_configs_multiple_configs(self):
        """Test loading multiple campaign configurations via get_campaign_configs."""
        # Given
        mock_s3_client = Mock()
        bucket_name = BucketName("test-bucket")

        # Create two different campaign configs
        campaign1_data = CampaignConfigFactory.build()
        campaign2_data = CampaignConfigFactory.build()

        campaign1_json = {"CampaignConfig": campaign1_data.model_dump(by_alias=True)}
        campaign2_json = {"CampaignConfig": campaign2_data.model_dump(by_alias=True)}

        mock_s3_client.list_objects.return_value = {"Contents": [{"Key": "campaign1.json"}, {"Key": "campaign2.json"}]}

        # Set up side_effect for get_object to return different responses
        def mock_get_object(**kwargs):
            key = kwargs.get("Key")
            if key == "campaign1.json":
                mock_response = MagicMock()
                mock_response.read.return_value = json.dumps(campaign1_json).encode()
                return {"Body": mock_response}
            if key == "campaign2.json":
                mock_response = MagicMock()
                mock_response.read.return_value = json.dumps(campaign2_json).encode()
                return {"Body": mock_response}
            return None

        mock_s3_client.get_object.side_effect = mock_get_object

        repo = CampaignRepo(mock_s3_client, bucket_name)

        # When
        configs = list(repo.get_campaign_configs())

        # Then
        expected_count = 2
        assert len(configs) == expected_count
        config_ids = [config.id for config in configs]
        assert campaign1_data.id in config_ids
        assert campaign2_data.id in config_ids

    def test_get_campaign_configs_empty_bucket(self):
        """Test loading from an empty S3 bucket."""
        # Given
        mock_s3_client = Mock()
        bucket_name = BucketName("test-bucket")

        mock_s3_client.list_objects.return_value = {"Contents": []}

        repo = CampaignRepo(mock_s3_client, bucket_name)

        # When
        configs = list(repo.get_campaign_configs())

        # Then
        assert len(configs) == 0
        assert configs == []

    def test_clear_campaign_cache(self):
        """Test that clear_campaign_cache removes cached data."""
        # Given
        mock_s3_client = Mock()
        bucket_name = BucketName("test-bucket")
        repo = CampaignRepo(mock_s3_client, bucket_name)

        # Set up mock data
        mock_campaign_data = CampaignConfigFactory.build()
        campaign_json = {"CampaignConfig": mock_campaign_data.model_dump(by_alias=True)}

        mock_s3_client.list_objects.return_value = {"Contents": [{"Key": "campaign1.json"}]}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(campaign_json).encode()
        mock_s3_client.get_object.return_value = {"Body": mock_response}

        # Load data to populate cache
        first_configs = list(repo.get_campaign_configs())
        assert len(first_configs) == 1

        # Clear the cache
        repo.clear_campaign_cache()

        # Reset mock to track calls after cache clear
        mock_s3_client.reset_mock()

        # When - should reload from S3 after cache clear
        second_configs = list(repo.get_campaign_configs())

        # Then
        assert len(second_configs) == 1

        # Verify S3 was called again after cache clear
        mock_s3_client.list_objects.assert_called_once()
        mock_s3_client.get_object.assert_called_once()

    def test_get_campaign_configs_caches_empty_list(self):
        """Test that even an empty result is cached to avoid repeated S3 calls."""
        # Given
        mock_s3_client = Mock()
        bucket_name = BucketName("test-bucket")

        mock_s3_client.list_objects.return_value = {"Contents": []}

        repo = CampaignRepo(mock_s3_client, bucket_name)

        # When - first call
        first_configs = list(repo.get_campaign_configs())

        # Reset mock to track second call
        mock_s3_client.reset_mock()

        # When - second call should use cached empty list
        second_configs = list(repo.get_campaign_configs())

        # Then
        assert len(first_configs) == 0
        assert len(second_configs) == 0

        # Verify S3 was NOT called on second request
        mock_s3_client.list_objects.assert_not_called()
        mock_s3_client.get_object.assert_not_called()
