from unittest.mock import MagicMock

import pytest
from boto3 import Session
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient
from yarl import URL

from eligibility_signposting_api.repos.factory import (
    dynamodb_resource_factory,
    firehose_client_factory,
    s3_service_factory,
)


@pytest.fixture
def mock_session() -> Session:
    return MagicMock(spec=Session)


def test_dynamodb_resource_factory_with_endpoint(mock_session: Session):
    mock_resource = MagicMock(spec=ServiceResource)
    mock_session.resource = MagicMock(return_value=mock_resource)
    endpoint = URL("http://localhost:4566")

    result = dynamodb_resource_factory(mock_session, endpoint)

    mock_session.resource.assert_called_once_with("dynamodb", endpoint_url="http://localhost:4566")
    assert result is mock_resource


def test_dynamodb_resource_factory_without_endpoint(mock_session):
    mock_resource = MagicMock(spec=ServiceResource)
    mock_session.resource = MagicMock(return_value=mock_resource)

    result = dynamodb_resource_factory(mock_session, None)

    mock_session.resource.assert_called_once_with("dynamodb", endpoint_url=None)
    assert result is mock_resource


def test_s3_service_factory_with_endpoint(mock_session):
    mock_client = MagicMock(spec=BaseClient)
    mock_session.client = MagicMock(return_value=mock_client)
    endpoint = URL("http://localhost:4566")

    result = s3_service_factory(mock_session, endpoint)

    mock_session.client.assert_called_once_with("s3", endpoint_url="http://localhost:4566")
    assert result is mock_client


def test_s3_service_factory_without_endpoint(mock_session):
    mock_client = MagicMock(spec=BaseClient)
    mock_session.client = MagicMock(return_value=mock_client)

    result = s3_service_factory(mock_session, None)

    mock_session.client.assert_called_once_with("s3", endpoint_url=None)
    assert result is mock_client


def test_firehose_service_factory_with_endpoint(mock_session):
    mock_client = MagicMock(spec=BaseClient)
    mock_session.client = MagicMock(return_value=mock_client)
    endpoint = URL("http://localhost:4566")

    result = firehose_client_factory(mock_session, endpoint)

    mock_session.client.assert_called_once_with("firehose", endpoint_url="http://localhost:4566")
    assert result is mock_client


def test_firehose_service_factory_without_endpoint(mock_session):
    mock_client = MagicMock(spec=BaseClient)
    mock_session.client = MagicMock(return_value=mock_client)

    result = firehose_client_factory(mock_session, None)

    mock_session.client.assert_called_once_with("firehose", endpoint_url=None)
    assert result is mock_client
