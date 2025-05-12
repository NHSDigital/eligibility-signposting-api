from eligibility_signposting_api.config import AwsRegion, config
from eligibility_signposting_api.repos.eligibility_repo import TableName
from eligibility_signposting_api.repos.rules_repo import BucketName


def test_config_with_env_variable(monkeypatch):
    monkeypatch.setenv("ENV", "PROD")

    config_data = config()

    assert config_data["aws_access_key_id"] is None
    assert config_data["aws_secret_access_key"] is None
    assert config_data["aws_default_region"] == AwsRegion("eu-west-1")
    assert config_data["eligibility_table_name"] == TableName("test_eligibility_datastore")
    assert config_data["rules_bucket_name"] == BucketName("test-rules-bucket")
