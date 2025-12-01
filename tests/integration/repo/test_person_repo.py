from typing import Any

import pytest
from faker import Faker
from hamcrest import assert_that, contains_inanyorder, has_entries

from eligibility_signposting_api.model.eligibility_status import NHSNumber
from eligibility_signposting_api.processors.hashing_service import HashingService
from eligibility_signposting_api.repos import NotFoundError
from eligibility_signposting_api.repos.person_repo import PersonRepo


def test_person_found(
    person_table: Any,
    persisted_person: NHSNumber,
    hashing_service: HashingService,
):
    # Given
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
    hashing_service: HashingService,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    repo = PersonRepo(person_table, hashing_service)

    # When, Then
    with pytest.raises(NotFoundError):
        repo.get_eligibility_data(nhs_number)


def test_items_found_but_person_attribute_type_not_found_raises_error(
    person_table: Any, persisted_person_with_no_person_attribute_type: NHSNumber, hashing_service: HashingService
):
    # Given
    repo = PersonRepo(person_table, hashing_service)

    ## When, Then
    with pytest.raises(NotFoundError):
        repo.get_eligibility_data(persisted_person_with_no_person_attribute_type)


def test_person_found_with_current_secret(
    person_table: Any, persisted_person: NHSNumber, hashing_service: HashingService
):
    # Given
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
    person_table: Any, persisted_person_previous: NHSNumber, hashing_service: HashingService
):
    # Given
    repo = PersonRepo(person_table, hashing_service)

    # When
    actual = repo.get_eligibility_data(persisted_person_previous)

    # Then
    nhs_num_hash = hashing_service.hash_with_previous_secret(persisted_person_previous)

    assert_that(
        actual.data,
        contains_inanyorder(
            has_entries({"NHS_NUMBER": nhs_num_hash, "ATTRIBUTE_TYPE": "PERSON"}),
            has_entries({"NHS_NUMBER": nhs_num_hash, "ATTRIBUTE_TYPE": "COHORTS"}),
        ),
    )


def test_person_found_without_hashed_nhs_num(
    person_table: Any, persisted_person_not_hashed: NHSNumber, hashing_service_without_previous: HashingService
):
    # Given
    repo = PersonRepo(person_table, hashing_service_without_previous)

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
    hashing_service: HashingService,
) -> None:
    # Given
    repo = PersonRepo(person_table, hashing_service)

    # When
    actual = repo.get_person_record(None)

    # Then
    assert actual is None


def test_get_person_record_returns_none_when_nhs_hash_is_empty_string(
    person_table: Any,
    hashing_service: HashingService,
) -> None:
    # Given
    repo = PersonRepo(person_table, hashing_service)

    # When
    actual = repo.get_person_record("")

    # Then
    assert actual is None


def test_get_person_record_returns_none_when_no_items_found(
    person_table: Any,
    hashing_service: HashingService,
) -> None:
    # Given
    repo = PersonRepo(person_table, hashing_service)
    nhs_hash_not_in_table = "nhs-number-that-does-not-exist"

    # When
    actual = repo.get_person_record(nhs_hash_not_in_table)

    # Then
    assert actual is None


def test_get_person_record_returns_none_when_items_have_no_person_attribute_type(
    person_table: Any,
    persisted_person_with_no_person_attribute_type: NHSNumber,
    hashing_service: HashingService,
) -> None:
    # Given
    repo = PersonRepo(person_table, hashing_service)
    nhs_hash = hashing_service.hash_with_current_secret(persisted_person_with_no_person_attribute_type)

    # When
    actual = repo.get_person_record(nhs_hash)

    # Then
    assert actual is None
