import json
from unittest.mock import MagicMock

import pytest

from eligibility_signposting_api.model.consumer_mapping import ConsumerId
from eligibility_signposting_api.repos.consumer_mapping_repo import BucketName, ConsumerMappingRepo


class TestConsumerMappingRepo:
    @pytest.fixture
    def mock_s3_client(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_s3_client):
        return ConsumerMappingRepo(s3_client=mock_s3_client, bucket_name=BucketName("test-bucket"))

    def test_get_permitted_campaign_ids_success(self, repo, mock_s3_client):
        # Given
        consumer_id = "user-123"

        # The expected output is just the IDs
        expected_campaign_ids = ["flu-2024", "covid-2024"]

        # The mocked S3 data must match the new schema (objects with description)
        mapping_data = {
            consumer_id: [
                {"CampaignConfigId": "flu-2024", "Description": "Flu Shot Description"},
                {"CampaignConfigId": "covid-2024", "Description": "Covid Shot Description"},
            ]
        }

        mock_s3_client.list_objects.return_value = {"Contents": [{"Key": "mappings.json"}]}

        body_json = json.dumps(mapping_data).encode("utf-8")
        mock_s3_client.get_object.return_value = {"Body": MagicMock(read=lambda: body_json)}

        # When
        result = repo.get_permitted_campaign_ids(ConsumerId(consumer_id))

        # Then
        assert result == expected_campaign_ids
        mock_s3_client.list_objects.assert_called_once_with(Bucket="test-bucket")
        mock_s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="mappings.json")

    def test_get_permitted_campaign_ids_returns_none_when_missing(self, repo, mock_s3_client):
        """
        Setup data where the consumer_id doesn't exist
        We must still use the valid schema (dicts inside the list) to pass Pydantic validation
        """
        valid_schema_data = {"other-user": [{"CampaignConfigId": "camp-1", "Description": "Some description"}]}

        mock_s3_client.list_objects.return_value = {"Contents": [{"Key": "mappings.json"}]}
        body_json = json.dumps(valid_schema_data).encode("utf-8")
        mock_s3_client.get_object.return_value = {"Body": MagicMock(read=lambda: body_json)}

        # When
        result = repo.get_permitted_campaign_ids(ConsumerId("missing-user"))

        # Then
        assert result is None
