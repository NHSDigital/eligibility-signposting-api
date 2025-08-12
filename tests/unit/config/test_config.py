import os

import pytest
from yarl import URL

from eligibility_signposting_api.config.config import LOG_LEVEL, AwsAccessKey, AwsRegion, AwsSecretAccessKey, config
from eligibility_signposting_api.repos.campaign_repo import BucketName
from eligibility_signposting_api.repos.person_repo import TableName


@pytest.fixture(autouse=True)
def clear_config_cache(monkeypatch):
    config.cache_clear()
    monkeypatch.delenv("ENV", raising=False)


def test_config_with_env_variable(monkeypatch):
    # Given:
    monkeypatch.setenv("ENV", "PROD")

    # When:
    config_data_with_env = config()

    # Then:
    assert os.getenv("ENV") == "PROD"
    assert config_data_with_env["aws_access_key_id"] is None
    assert config_data_with_env["aws_secret_access_key"] is None
    assert config_data_with_env["aws_default_region"] == AwsRegion("eu-west-1")
    assert config_data_with_env["dynamodb_endpoint"] is None
    assert config_data_with_env["person_table_name"] == TableName("test_eligibility_datastore")
    assert config_data_with_env["s3_endpoint"] is None
    assert config_data_with_env["rules_bucket_name"] == BucketName("test-rules-bucket")
    assert config_data_with_env["log_level"] == LOG_LEVEL


def test_config_without_env_variable():
    # Given: The environment variable "ENV" isn't set
    # When:
    config_data_without_env = config()

    # Then:
    assert os.getenv("ENV") is None
    assert config_data_without_env["aws_access_key_id"] == AwsAccessKey("dummy_key")
    assert config_data_without_env["aws_secret_access_key"] == AwsSecretAccessKey("dummy_secret")
    assert config_data_without_env["aws_default_region"] == AwsRegion("eu-west-1")
    assert config_data_without_env["dynamodb_endpoint"] == URL("http://localhost:4566")
    assert config_data_without_env["person_table_name"] == TableName("test_eligibility_datastore")
    assert config_data_without_env["s3_endpoint"] == URL("http://localhost:4566")
    assert config_data_without_env["rules_bucket_name"] == BucketName("test-rules-bucket")
    assert config_data_without_env["log_level"] == LOG_LEVEL
