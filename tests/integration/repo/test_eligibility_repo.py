from typing import Any

import pytest
from faker import Faker
from hamcrest import assert_that, contains_inanyorder, has_entries

from eligibility_signposting_api.model.eligibility import NHSNumber
from eligibility_signposting_api.repos import NotFoundError
from eligibility_signposting_api.repos.eligibility_repo import EligibilityRepo


def test_person_found(eligibility_table: Any, persisted_person: NHSNumber):
    # Given
    repo = EligibilityRepo(eligibility_table)

    # When
    actual = repo.get_eligibility_data(persisted_person)

    # Then
    assert_that(
        actual,
        contains_inanyorder(
            has_entries({"NHS_NUMBER": f"PERSON#{persisted_person}", "ATTRIBUTE_TYPE": "PERSON"}),
            has_entries({"NHS_NUMBER": f"PERSON#{persisted_person}", "ATTRIBUTE_TYPE": "COHORTS"}),
            has_entries({"NHS_NUMBER": f"PERSON#{persisted_person}", "ATTRIBUTE_TYPE": "COVID"}),
            has_entries({"NHS_NUMBER": f"PERSON#{persisted_person}", "ATTRIBUTE_TYPE": "RSV"}),
        ),
    )


def test_person_not_found(eligibility_table: Any, faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    repo = EligibilityRepo(eligibility_table)

    # When, Then
    with pytest.raises(NotFoundError):
        repo.get_eligibility_data(nhs_number)
