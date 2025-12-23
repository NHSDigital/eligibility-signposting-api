import boto3
import pytest
from moto import mock_aws

from eligibility_signposting_api.repos.secret_repo import SecretRepo


@pytest.fixture
def aws_setup():
    """Create AWS secrets in moto environment with stages."""
    with mock_aws():
        sm = boto3.client("secretsmanager", region_name="eu-west-2")

        sm.create_secret(
            Name="my-secret",
            SecretString="current-value",
        )

        sm.put_secret_value(
            SecretId="my-secret",
            SecretString="previous-value",
            VersionStages=["AWSPREVIOUS"],
        )

        yield sm


@pytest.fixture
def repo(aws_setup):
    """SecretRepo using Moto SecretsManager."""
    return SecretRepo(secret_manager=aws_setup)


def test_get_secret_current(repo):
    result = repo.get_secret_current("my-secret")
    assert result == {"AWSCURRENT": "current-value"}


def test_get_secret_previous(repo):
    result = repo.get_secret_previous("my-secret")
    assert result == {"AWSPREVIOUS": "previous-value"}


def test_get_secret_missing(repo):
    result = repo.get_secret_current("does-not-exist")
    assert result == {}
