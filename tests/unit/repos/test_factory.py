from unittest.mock import Mock

import pytest
from yarl import URL

from eligibility_signposting_api.repos.factory import dynamodb_resource_factory, s3_service_factory


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


def test_dynamodb_resource_factory_with_endpoint(mock_session: Session):
    mock_resource = Mock()
    mock_session.resource.return_value = mock_resource
    endpoint = URL("http://localhost:4566")

    result = dynamodb_resource_factory(mock_session, endpoint)

    mock_session.resource.assert_called_once_with("dynamodb", endpoint_url="http://localhost:4566")
    assert result is mock_resource


def test_dynamodb_resource_factory_without_endpoint(mock_session):
    mock_resource = Mock()
    mock_session.resource.return_value = mock_resource

    result = dynamodb_resource_factory(mock_session, None)

    mock_session.resource.assert_called_once_with("dynamodb", endpoint_url=None)
    assert result is mock_resource


def test_s3_service_factory_with_endpoint(mock_session):
    mock_client = Mock()
    mock_session.client.return_value = mock_client
    endpoint = URL("http://localhost:4566")

    result = s3_service_factory(mock_session, endpoint)

    mock_session.client.assert_called_once_with("s3", endpoint_url="http://localhost:4566")
    assert result is mock_client


def test_s3_service_factory_without_endpoint(mock_session):
    mock_client = Mock()
    mock_session.client.return_value = mock_client

    result = s3_service_factory(mock_session, None)

    mock_session.client.assert_called_once_with("s3", endpoint_url=None)
    assert result is mock_client
