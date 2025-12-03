from typing import Any

import pytest
from faker import Faker
from hamcrest import assert_that, contains_inanyorder, has_entries

from eligibility_signposting_api.model.eligibility_status import NHSNumber
from eligibility_signposting_api.processors.hashing_service import HashingService
from eligibility_signposting_api.repos import NotFoundError
from eligibility_signposting_api.repos.person_repo import PersonRepo
from tests.integration.conftest import AWS_CURRENT_SECRET, AWS_PREVIOUS_SECRET


def test_person_found(
    person_table: Any,
    persisted_person: NHSNumber,
    hashing_service_factory: HashingService,
):
    # Given
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)

    # When
    actual = repo.get_eligibility_data(persisted_person)

    # Then
    nhs_num_hash = hashing_service.hash_with_current_secret(persisted_person)

    assert_that(
        actual.data,
        contains_inanyorder(
            has_entries({"NHS_NUMBER": nhs_num_hash, "ATTRIBUTE_TYPE": "PERSON"}),
            has_entries({"NHS_NUMBER": nhs_num_hash, "ATTRIBUTE_TYPE": "COHORTS"}),
        ),
    )


def test_items_not_found_raises_error(
    person_table: Any,
    faker: Faker,
    hashing_service_factory: HashingService,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)

    # When, Then
    with pytest.raises(NotFoundError):
        repo.get_eligibility_data(nhs_number)


def test_items_found_but_person_attribute_type_not_found_raises_error(
    person_table: Any,
    persisted_person_with_no_person_attribute_type: NHSNumber,
    hashing_service_factory: HashingService,
):
    # Given
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)

    ## When, Then
    with pytest.raises(NotFoundError):
        repo.get_eligibility_data(persisted_person_with_no_person_attribute_type)


def test_person_found_with_current_secret(
    person_table: Any, persisted_person: NHSNumber, hashing_service_factory: HashingService
):
    # Given
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)

    # When
    actual = repo.get_eligibility_data(persisted_person)

    # Then
    nhs_num_hash = hashing_service.hash_with_current_secret(persisted_person)

    assert_that(
        actual.data,
        contains_inanyorder(
            has_entries({"NHS_NUMBER": nhs_num_hash, "ATTRIBUTE_TYPE": "PERSON"}),
            has_entries({"NHS_NUMBER": nhs_num_hash, "ATTRIBUTE_TYPE": "COHORTS"}),
        ),
    )


def test_person_found_with_previous_secret(
    person_table: Any, persisted_person_factory: NHSNumber, hashing_service_factory: HashingService
):
    # Given
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)

    # When
    persisted_person = persisted_person_factory(secret_key="previous")
    actual = repo.get_eligibility_data(persisted_person)

    # Then
    nhs_num_hash = hashing_service.hash_with_previous_secret(persisted_person)

    assert_that(
        actual.data,
        contains_inanyorder(
            has_entries({"NHS_NUMBER": nhs_num_hash, "ATTRIBUTE_TYPE": "PERSON"}),
            has_entries({"NHS_NUMBER": nhs_num_hash, "ATTRIBUTE_TYPE": "COHORTS"}),
        ),
    )


def test_person_found_without_hashed_nhs_num(
    person_table: Any, persisted_person_not_hashed: NHSNumber, hashing_service_factory: HashingService
):
    # Given
    hashing_service = hashing_service_factory(previous=None)
    repo = PersonRepo(person_table, hashing_service)

    # When
    actual = repo.get_eligibility_data(persisted_person_not_hashed)

    # Then
    nhs_number = persisted_person_not_hashed
    assert_that(
        actual.data,
        contains_inanyorder(
            has_entries({"NHS_NUMBER": nhs_number, "ATTRIBUTE_TYPE": "PERSON"}),
            has_entries({"NHS_NUMBER": nhs_number, "ATTRIBUTE_TYPE": "COHORTS"}),
        ),
    )


def test_get_person_record_returns_none_when_nhs_hash_is_none(
    person_table: Any,
    hashing_service_factory: HashingService,
) -> None:
    # Given
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)

    # When
    actual = repo.get_person_record(None)

    # Then
    assert actual is None


def test_get_person_record_returns_none_when_nhs_hash_is_empty_string(
    person_table: Any,
    hashing_service_factory: HashingService,
) -> None:
    # Given
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)

    # When
    actual = repo.get_person_record("")

    # Then
    assert actual is None


def test_get_person_record_returns_none_when_no_items_found(
    person_table: Any,
    hashing_service_factory: HashingService,
) -> None:
    # Given
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)
    nhs_hash_not_in_table = "nhs-number-that-does-not-exist"

    # When
    actual = repo.get_person_record(nhs_hash_not_in_table)

    # Then
    assert actual is None


def test_get_person_record_returns_none_when_items_have_no_person_attribute_type(
    person_table: Any,
    persisted_person_with_no_person_attribute_type: NHSNumber,
    hashing_service_factory: HashingService,
) -> None:
    # Given
    hashing_service = hashing_service_factory()
    repo = PersonRepo(person_table, hashing_service)
    nhs_hash = hashing_service.hash_with_current_secret(persisted_person_with_no_person_attribute_type)

    # When
    actual = repo.get_person_record(nhs_hash)

    # Then
    assert actual is None


@pytest.mark.parametrize(
    ("has_awscurrent_key", "has_awsprevious_key", "dynamodb_record", "expected_result"),
    [
        # If  key AWSCURRENT exists,      record AWSCurrent exists,
        # and key AWSPREVIOUS not exists, record AWSPREVIOUS not exist,
        # and record plain does not exist
        # then return record AWSCurrent with key AWSCurrent
        (True, False, "current", "current_record"),
        # If  key AWSCURRENT exists,      record AWSCurrent not exists,
        # and key AWSPREVIOUS not exists, record AWSPREVIOUS not exist,
        # and record plain does not exist
        # then person not found
        (True, False, None, "person_not_found"),
        # If  key AWSCURRENT exists,      record AWSCurrent not exists,
        # and key AWSPREVIOUS not exists, record AWSPREVIOUS not exist,
        # and record plain does exist
        # then return record plain
        (True, False, "not_hashed", "not_hashed_record"),
        # If  key AWSCURRENT not exists, record AWSCurrent not exists,
        # and key AWSPREVIOUS exists,    record AWSPREVIOUS exist,
        # and record plain does not exist
        # then return record AWSPrevious with key AWSPrevious
        (False, True, "previous", "previous_record"),
        # If  key AWSCURRENT not exists, record AWSCurrent not exists,
        # and key AWSPREVIOUS exists,    record AWSPREVIOUS not exist,
        # and record plain does not exist
        # then person not found
        (False, True, None, "person_not_found"),
        # If  key AWSCURRENT not exists, record AWSCurrent not exists,
        # and key AWSPREVIOUS exists,    record AWSPREVIOUS not exist,
        # and record plain does exist
        # then person not found
        (False, True, "not_hashed", "person_not_found"),
        # If  key AWSCURRENT not exists,  record AWSCurrent not exists,
        # and key AWSPREVIOUS not exists, record AWSPREVIOUS not exist,
        # and record plain does exist
        # then return record plain
        (False, False, "not_hashed", "not_hashed_record"),
        # If  key AWSCURRENT not exists,  record AWSCurrent not exists,
        # and key AWSPREVIOUS not exists, record AWSPREVIOUS not exist,
        # and record plain does not exist
        # then return person not found
        (False, False, None, "person_not_found"),
    ],
)
def test_secret_key_scenarios(  # noqa: PLR0913
    has_awscurrent_key: bool,  # noqa: FBT001
    has_awsprevious_key: bool,  # noqa: FBT001
    dynamodb_record: str | None,
    expected_result: str,
    person_table: Any,
    persisted_person_factory: NHSNumber,
    hashing_service_factory: HashingService,
):
    """
    Test scenarios for resolving which DynamoDB record to return based on the
    presence of AWSCURRENT key, AWSPREVIOUS key, and not hashed records.

    Scenarios
    ---------

    1.  AWSCURRENT key exists; AWSCURRENT record exists.
        AWSPREVIOUS key does not exist; AWSPREVIOUS record does not exist.
        Not hashed record does not exist.
        → Expect: return AWSCURRENT record ("current_record").

        Params:
            (True, False, "current", "current_record")

    2.  AWSCURRENT key exists; AWSCURRENT record does not exist.
        AWSPREVIOUS key does not exist; AWSPREVIOUS record does not exist.
        Not hashed record does not exist.
        → Expect: person not found ("person_not_found").

        Params:
            (True, False, None, "person_not_found")

    3.  AWSCURRENT key exists; AWSCURRENT record does not exist.
        AWSPREVIOUS key does not exist; AWSPREVIOUS record does not exist.
        Not hashed record exists.
        → Expect: return not hashed record ("not_hashed_record").

        Params:
            (True, False, "not_hashed", "not_hashed_record")

    4.  AWSCURRENT key does not exist; AWSCURRENT record does not exist.
        AWSPREVIOUS key exists; AWSPREVIOUS record exists.
        Not hashed record does not exist.
        → Expect: return AWSPREVIOUS record ("previous_record").

        Params:
            (False, True, "previous", "previous_record")

    5.  AWSCURRENT key does not exist; AWSCURRENT record does not exist.
        AWSPREVIOUS key exists; AWSPREVIOUS record does not exist.
        Not hashed record does not exist.
        → Expect: person not found ("person_not_found").

        Params:
            (False, True, None, "person_not_found")

    6.  AWSCURRENT key does not exist; AWSCURRENT record does not exist.
        AWSPREVIOUS key exists; AWSPREVIOUS record does not exist.
        Not hashed record exists.
        → Expect: person not found ("person_not_found").

        Params:
            (False, True, "not_hashed", "person_not_found")

    7.  AWSCURRENT key does not exist; AWSCURRENT record does not exist.
        AWSPREVIOUS key does not exist; AWSPREVIOUS record does not exist.
        Not hashed record exists.
        → Expect: return not hashed record ("not_hashed_record").

        Params:
            (False, False, "not_hashed", "not_hashed_record")

    8.  AWSCURRENT key does not exist; AWSCURRENT record does not exist.
        AWSPREVIOUS key does not exist; AWSPREVIOUS record does not exist.
        Not hashed record does not exist.
        → Expect: person not found ("person_not_found").

        Params:
            (False, False, None, "person_not_found")
    """

    # Given
    current = None if not has_awscurrent_key else AWS_CURRENT_SECRET
    previous = None if not has_awsprevious_key else AWS_PREVIOUS_SECRET
    hashing_service = hashing_service_factory(current=current, previous=previous)

    persisted_person = persisted_person_factory(secret_key=dynamodb_record) if dynamodb_record else None

    repo = PersonRepo(person_table, hashing_service)

    if expected_result == "person_not_found":
        with pytest.raises(NotFoundError):
            repo.get_eligibility_data(persisted_person)
    else:
        actual = repo.get_eligibility_data(persisted_person)

        if expected_result == "current_record":
            nhs_num_value = hashing_service.hash_with_current_secret(persisted_person)
        if expected_result == "previous_record":
            nhs_num_value = hashing_service.hash_with_previous_secret(persisted_person)
        if expected_result == "not_hashed_record":
            nhs_num_value = persisted_person

        assert_that(
            actual.data,
            contains_inanyorder(
                has_entries({"NHS_NUMBER": nhs_num_value, "ATTRIBUTE_TYPE": "PERSON"}),
                has_entries({"NHS_NUMBER": nhs_num_value, "ATTRIBUTE_TYPE": "COHORTS"}),
            ),
        )
