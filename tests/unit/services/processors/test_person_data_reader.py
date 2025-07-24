import pytest
from hamcrest import assert_that, is_

from eligibility_signposting_api.services.processors.person_data_reader import PersonDataReader


@pytest.fixture
def person_data_reader():
    return PersonDataReader()


def test_get_person_cohorts_empty_data(person_data_reader):
    result = person_data_reader.get_person_cohorts([])
    assert_that(result, is_(set()))


def test_get_person_cohorts_no_cohorts_attribute_type(person_data_reader):
    no_cohorts_type = [
        {"ATTRIBUTE_TYPE": "NAME", "VALUE": "John Doe"},
        {"ATTRIBUTE_TYPE": "AGE", "VALUE": 30},
    ]
    result = person_data_reader.get_person_cohorts(no_cohorts_type)
    assert_that(result, is_(set()))


def test_get_person_cohorts_no_cohort_map_key(person_data_reader):
    no_cohorts_map = [
        {"ATTRIBUTE_TYPE": "COHORTS", "OTHER_FIELD": "value"},
    ]
    result = person_data_reader.get_person_cohorts(no_cohorts_map)
    assert_that(result, is_(set()))


def test_get_person_cohorts_single_cohort(person_data_reader):
    single_cohorts = [
        {
            "ATTRIBUTE_TYPE": "COHORTS",
            "COHORT_MEMBERSHIPS": [{"COHORT_LABEL": "flu_65+_autumnwinter2023", "DATE_JOINED": "20231020"}],
        },
        {"ATTRIBUTE_TYPE": "NAME", "VALUE": "Jane Smith"},
    ]
    result = person_data_reader.get_person_cohorts(single_cohorts)
    assert_that(result, is_({"flu_65+_autumnwinter2023"}))


def test_get_person_cohorts_multiple_cohorts(person_data_reader):
    multiple_cohorts = [
        {
            "ATTRIBUTE_TYPE": "COHORTS",
            "COHORT_MEMBERSHIPS": [
                {"COHORT_LABEL": "COHORT_B", "DATE_JOINED": "20231020"},
                {"COHORT_LABEL": "COHORT_C", "DATE_JOINED": "20241020"},
            ],
        },
        {"ATTRIBUTE_TYPE": "AGE", "VALUE": 45},
    ]
    result = person_data_reader.get_person_cohorts(multiple_cohorts)
    assert_that(result, is_({"COHORT_B", "COHORT_C"}))


def test_get_person_cohorts_mixed_data(person_data_reader):
    mixed_data = [
        {
            "ATTRIBUTE_TYPE": "COHORTS",
            "COHORT_MEMBERSHIPS": [
                {"COHORT_LABEL": "COHORT_D", "DATE_JOINED": "20231020"},
                {"COHORT_LABEL": "COHORT_E", "DATE_JOINED": "20241020"},
            ],
        },
        {"ATTRIBUTE_TYPE": "NAME", "VALUE": "Alice"},
        {"ATTRIBUTE_TYPE": "ADDRESS", "VALUE": "123 Main St"},
    ]

    result = person_data_reader.get_person_cohorts(mixed_data)
    assert_that(result, is_({"COHORT_D", "COHORT_E"}))


def test_get_person_cohorts_with_other_attribute_types_present(person_data_reader):
    data = [
        {"ATTRIBUTE_TYPE": "COHORTS", "COHORT_MEMBERSHIPS": [{"COHORT_LABEL": "COHORT_F", "DATE_JOINED": "20231020"}]},
        {"ATTRIBUTE_TYPE": "NAME", "VALUE": "Charlie"},
        {"ATTRIBUTE_TYPE": "AGE", "VALUE": 25},
    ]

    result = person_data_reader.get_person_cohorts(data)
    assert_that(result, is_({"COHORT_F"}))
