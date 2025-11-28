from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.repos import NotFoundError, PersonRepo


@pytest.fixture
def dynamodb_setup():
    """Create a DynamoDB table with moto and insert test person records."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        table = dynamodb.create_table(
            TableName="person-table",
            KeySchema=[{"AttributeName": "NHS_NUMBER", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "NHS_NUMBER", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        yield table


@pytest.fixture
def hashing_service():
    """Mock hashing service with predictable outputs."""
    svc = MagicMock()

    # Simulate deterministic hashes:
    svc.hash_with_current_secret.return_value = "hashed-current"
    svc.hash_with_previous_secret.return_value = "hashed-prev"

    return svc


@pytest.fixture
def repo(dynamodb_setup, hashing_service):
    """PersonRepo instance with moto DynamoDB and mocked hashing."""
    return PersonRepo(
        table=dynamodb_setup,
        hashing_service=hashing_service,
    )


def test_get_person_record_found_using_current_secret_hashed_nhs_number(repo, dynamodb_setup):
    dynamodb_setup.put_item(Item={"NHS_NUMBER": "hashed-current", "ATTRIBUTE_TYPE": "PERSON"})

    result = repo.get_person_record("hashed-current")

    assert isinstance(result, list)
    assert result[0]["NHS_NUMBER"] == "hashed-current"
    assert result[0]["ATTRIBUTE_TYPE"] == "PERSON"


def test_get_person_record_returns_none_with_attribute_type_not_person(repo, dynamodb_setup):
    dynamodb_setup.put_item(Item={"NHS_NUMBER": "hashed-current", "ATTRIBUTE_TYPE": "COHORTS"})

    result = repo.get_person_record("hashed-current")
    assert result is None


def test_get_eligibility_data_returns_person_with_current_hashed_nhs_number(repo, dynamodb_setup):
    dynamodb_setup.put_item(Item={"NHS_NUMBER": "hashed-current", "ATTRIBUTE_TYPE": "PERSON"})

    result = repo.get_eligibility_data("hashed-current")

    assert isinstance(result, Person)


def test_get_eligibility_data_returns_person_with_previous_hashed_nhs_number(dynamodb_setup):
    dynamodb_setup.put_item(Item={"NHS_NUMBER": "hashed-prev", "ATTRIBUTE_TYPE": "PERSON"})

    hashing_service = MagicMock()
    hashing_service.hash_with_current_secret.return_value = None
    hashing_service.hash_with_previous_secret.return_value = "hashed-prev"

    repo = PersonRepo(
        table=dynamodb_setup,
        hashing_service=hashing_service,
    )

    result = repo.get_eligibility_data("hashed-prev")

    assert isinstance(result, Person)


def test_get_eligibility_data_returns_person_with_not_hashed_nhs_number(dynamodb_setup):
    dynamodb_setup.put_item(Item={"NHS_NUMBER": "1234567890", "ATTRIBUTE_TYPE": "PERSON"})

    hashing_service = MagicMock()
    hashing_service.hash_with_current_secret.return_value = None
    hashing_service.hash_with_previous_secret.return_value = None

    repo = PersonRepo(
        table=dynamodb_setup,
        hashing_service=hashing_service,
    )

    result = repo.get_eligibility_data("1234567890")

    assert isinstance(result, Person)


def test_get_eligibility_data_not_found_error(repo, dynamodb_setup, caplog):
    dynamodb_setup.put_item(Item={"NHS_NUMBER": "9876543210", "ATTRIBUTE_TYPE": "PERSON", "value": "unhashed"})

    with pytest.raises(NotFoundError):
        repo.get_eligibility_data("1234567890")

    # Ensure all error logs were generated
    log_text = caplog.text
    assert "AWSCURRENT" in log_text
    assert "AWSPREVIOUS" in log_text
    assert "not hashed" in log_text
