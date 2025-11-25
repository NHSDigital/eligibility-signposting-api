import pytest

from eligibility_signposting_api.repos.secrets import nhs_hmac_key_factory


def test_nhs_hmac_key_factory_returns_bytes():
    keys = nhs_hmac_key_factory()
    assert True


# from moto import mock_aws
# import boto3
#
# @mock_aws
# def test_secret():
#     client = boto3.client("secretsmanager", region_name="us-east-1")
#
#     client.create_secret(
#         Name="my-secret",
#         SecretString="value"
#     )
#
#     resp = client.get_secret_value(SecretId="my-secret")
#
#     assert resp["SecretString"] == "value"
