import pytest
from freezegun import freeze_time
from hamcrest import assert_that, equal_to

from eligibility_signposting_api.model.rules import RuleOperator
from eligibility_signposting_api.services.rules.operators import Operator, OperatorRegistry

# Test cases: person_data, rule_operator, rule_value, expected, test_comment
cases: list[tuple[str | None, RuleOperator, str | None, bool, str]] = []

# Equals
cases += [
    ("42", RuleOperator.equals, "42", True, ""),
    ("", RuleOperator.equals, "42", False, ""),
    (None, RuleOperator.equals, "42", False, ""),
    ("99", RuleOperator.equals, "42", False, ""),
    ("-1", RuleOperator.equals, "-1", True, ""),
    ("0", RuleOperator.equals, "-1", False, ""),
    ("", RuleOperator.equals, "-1", False, ""),
    (None, RuleOperator.equals, "-1", False, ""),
    ("", RuleOperator.equals, "", False, ""),
    (None, RuleOperator.equals, "", False, ""),
    ("", RuleOperator.equals, None, False, ""),
    (None, RuleOperator.equals, None, False, ""),
    ("Fourtytwo", RuleOperator.equals, "42", False, ""),
]

# Greater Than
cases += [
    ("101", RuleOperator.gt, "100", True, ""),
    ("100", RuleOperator.gt, "100", False, ""),
    ("99", RuleOperator.gt, "100", False, ""),
    ("", RuleOperator.gt, "100", False, ""),
    (None, RuleOperator.gt, "100", False, ""),
    ("0", RuleOperator.gt, "-1", True, ""),
    ("-1", RuleOperator.gt, "-1", False, ""),
    ("-2", RuleOperator.gt, "-1", False, ""),
    ("", RuleOperator.gt, "-1", False, ""),
    (None, RuleOperator.gt, "-1", False, ""),
]

# Less Than
cases += [
    ("42", RuleOperator.lt, "100", True, ""),
    ("99", RuleOperator.lt, "100", True, ""),
    ("100", RuleOperator.lt, "100", False, ""),
    ("101", RuleOperator.lt, "100", False, ""),
    ("", RuleOperator.lt, "100", False, ""),
    (None, RuleOperator.lt, "100", False, ""),
    ("-2", RuleOperator.lt, "-1", True, ""),
    ("-1", RuleOperator.lt, "-1", False, ""),
    ("0", RuleOperator.lt, "-1", False, ""),
    ("", RuleOperator.lt, "-1", False, ""),
    (None, RuleOperator.lt, "-1", False, ""),
]

# Not Equals
cases += [
    ("98", RuleOperator.ne, "27", True, ""),
    ("", RuleOperator.ne, "27", False, ""),
    (None, RuleOperator.ne, "27", False, ""),
    ("27", RuleOperator.ne, "27", False, ""),
    ("-1", RuleOperator.ne, "-1", False, ""),
    ("0", RuleOperator.ne, "-1", True, ""),
    ("", RuleOperator.ne, "-1", False, ""),
    (None, RuleOperator.ne, "-1", False, ""),
]

# Greater Than or Equal
cases += [
    ("100", RuleOperator.gte, "100", True, ""),
    ("101", RuleOperator.gte, "100", True, ""),
    ("99", RuleOperator.gte, "100", False, ""),
    ("", RuleOperator.gte, "100", False, ""),
    (None, RuleOperator.gte, "100", False, ""),
    ("0", RuleOperator.gte, "-1", True, ""),
    ("-1", RuleOperator.gte, "-1", True, ""),
    ("-2", RuleOperator.gte, "-1", False, ""),
    ("", RuleOperator.gte, "-1", False, ""),
    (None, RuleOperator.gte, "-1", False, ""),
]

# Less Than or Equal
cases += [
    ("99", RuleOperator.lte, "100", True, ""),
    ("100", RuleOperator.lte, "100", True, ""),
    ("101", RuleOperator.lte, "100", False, ""),
    ("", RuleOperator.lte, "100", False, ""),
    (None, RuleOperator.lte, "100", False, ""),
    ("-2", RuleOperator.lte, "-1", True, ""),
    ("-1", RuleOperator.lte, "-1", True, ""),
    ("0", RuleOperator.lte, "-1", False, ""),
    ("", RuleOperator.lte, "-1", False, ""),
    (None, RuleOperator.lte, "-1", False, ""),
]

# Is Null
cases += [
    ("", RuleOperator.is_null, None, True, ""),
    (None, RuleOperator.is_null, None, True, ""),
    ("email_flag", RuleOperator.is_null, None, False, ""),
    (42, RuleOperator.is_null, None, False, ""),
]

# Is Not Null
cases += [
    ("", RuleOperator.is_not_null, None, False, ""),
    (None, RuleOperator.is_not_null, None, False, ""),
    ("email_flag", RuleOperator.is_not_null, None, True, ""),
    (42, RuleOperator.is_not_null, None, True, ""),
]

# Between - inclusive
cases += [
    ("0", RuleOperator.is_between, "1,3", False, ""),
    ("1", RuleOperator.is_between, "1,3", True, ""),
    ("2", RuleOperator.is_between, "1,3", True, ""),
    ("3", RuleOperator.is_between, "1,3", True, ""),
    ("4", RuleOperator.is_between, "1,3", False, ""),
    ("", RuleOperator.is_between, "1,3", False, ""),
    (None, RuleOperator.is_between, "1,3", False, ""),
    ("0", RuleOperator.is_between, "3,1", False, ""),
    ("1", RuleOperator.is_between, "3,1", True, ""),
    ("2", RuleOperator.is_between, "3,1", True, ""),
    ("3", RuleOperator.is_between, "3,1", True, ""),
    ("4", RuleOperator.is_between, "3,1", False, ""),
    ("", RuleOperator.is_between, "3,1", False, ""),
    (None, RuleOperator.is_between, "3,1", False, ""),
    ("2", RuleOperator.is_between, "3,3", False, ""),
    ("3", RuleOperator.is_between, "3,3", True, ""),
    ("4", RuleOperator.is_between, "3,3", False, ""),
    ("", RuleOperator.is_between, "3,3", False, ""),
    (None, RuleOperator.is_between, "3,3", False, ""),
    ("20100301", RuleOperator.is_between, "20100302,20100304", False, ""),
    ("20100302", RuleOperator.is_between, "20100302,20100304", True, ""),
    ("20100303", RuleOperator.is_between, "20100302,20100304", True, ""),
    ("20100304", RuleOperator.is_between, "20100302,20100304", True, ""),
    ("20100305", RuleOperator.is_between, "20100302,20100304", False, ""),
    ("", RuleOperator.is_between, "20100302,20100304", False, ""),
    (None, RuleOperator.is_between, "20100302,20100304", False, ""),
]

# Not Between
cases += [
    ("0", RuleOperator.is_not_between, "1,3", True, ""),
    ("1", RuleOperator.is_not_between, "1,3", False, ""),
    ("2", RuleOperator.is_not_between, "1,3", False, ""),
    ("3", RuleOperator.is_not_between, "1,3", False, ""),
    ("4", RuleOperator.is_not_between, "1,3", True, ""),
    ("", RuleOperator.is_not_between, "1,3", False, ""),
    (None, RuleOperator.is_not_between, "1,3", False, ""),
    ("0", RuleOperator.is_not_between, "3,1", True, ""),
    ("1", RuleOperator.is_not_between, "3,1", False, ""),
    ("2", RuleOperator.is_not_between, "3,1", False, ""),
    ("3", RuleOperator.is_not_between, "3,1", False, ""),
    ("4", RuleOperator.is_not_between, "3,1", True, ""),
    ("", RuleOperator.is_not_between, "3,1", False, ""),
    (None, RuleOperator.is_not_between, "3,1", False, ""),
    ("2", RuleOperator.is_not_between, "3,3", True, ""),
    ("3", RuleOperator.is_not_between, "3,3", False, ""),
    ("4", RuleOperator.is_not_between, "3,3", True, ""),
    ("", RuleOperator.is_not_between, "3,3", False, ""),
    (None, RuleOperator.is_not_between, "3,3", False, ""),
]

# Is Empty
cases += [
    ("", RuleOperator.is_empty, None, True, ""),
    (",", RuleOperator.is_empty, None, True, ""),
    (",,,,", RuleOperator.is_empty, None, True, ""),
    (", , , ,", RuleOperator.is_empty, None, True, ""),
    ("  ,  ,  ,  ,  ", RuleOperator.is_empty, None, True, ""),
    (None, RuleOperator.is_empty, None, True, ""),
    ("              ", RuleOperator.is_empty, None, True, ""),
    ("a", RuleOperator.is_empty, None, False, ""),
    ("this is not empty", RuleOperator.is_empty, None, False, ""),
    ("a,", RuleOperator.is_empty, None, False, ""),
    (",a", RuleOperator.is_empty, None, False, ""),
    ("a,b,c", RuleOperator.is_empty, None, False, ""),
]

# Is Not Empty
cases += [
    ("a", RuleOperator.is_not_empty, None, True, ""),
    ("this is not empty", RuleOperator.is_not_empty, None, True, ""),
    ("a,", RuleOperator.is_not_empty, None, True, ""),
    (",a", RuleOperator.is_not_empty, None, True, ""),
    ("a,b,c", RuleOperator.is_not_empty, None, True, ""),
    ("", RuleOperator.is_not_empty, None, False, ""),
    (",", RuleOperator.is_not_empty, None, False, ""),
    (",,,,", RuleOperator.is_not_empty, None, False, ""),
    (", , , ,", RuleOperator.is_not_empty, None, False, ""),
    ("  ,  ,  ,  ,  ", RuleOperator.is_not_empty, None, False, ""),
    (None, RuleOperator.is_not_empty, None, False, ""),
    ("              ", RuleOperator.is_not_empty, None, False, ""),
]

# Is True
cases += [
    (True, RuleOperator.is_true, None, True, ""),
    (False, RuleOperator.is_true, None, False, ""),
    ("", RuleOperator.is_true, None, False, ""),
    (None, RuleOperator.is_true, None, False, ""),
    ("True", RuleOperator.is_true, None, False, ""),
]

# Is False
cases += [
    (False, RuleOperator.is_false, None, True, ""),
    (True, RuleOperator.is_false, None, False, ""),
    ("", RuleOperator.is_false, None, False, ""),
    (None, RuleOperator.is_false, None, False, ""),
    ("False", RuleOperator.is_false, None, False, ""),
]

# Contains
cases += [
    ("A12 3DC", RuleOperator.contains, "A12", True, ""),
    ("A12", RuleOperator.contains, "A12", True, ""),
    (None, RuleOperator.contains, "A12", False, ""),
    ("", RuleOperator.contains, "A12", False, ""),
    ("A23", RuleOperator.contains, "A12", False, ""),
    (23, RuleOperator.contains, "A12", False, ""),
]

# Not Contains
cases += [
    ("A22", RuleOperator.not_contains, "A12", True, ""),
    (None, RuleOperator.not_contains, "A12", True, ""),
    ("", RuleOperator.not_contains, "A12", True, ""),
    (23, RuleOperator.not_contains, "A12", True, ""),
    ("A12", RuleOperator.not_contains, "A12", False, ""),
]

# Starts With
cases += [
    ("YY66", RuleOperator.starts_with, "YY66", True, ""),
    ("YY66095", RuleOperator.starts_with, "YY66", True, ""),
    ("BB11", RuleOperator.starts_with, "YY66", False, ""),
    ("BYY66095", RuleOperator.starts_with, "YY66", False, ""),
    ("  YY66", RuleOperator.starts_with, "YY66", False, ""),
    (None, RuleOperator.starts_with, "YY66", False, ""),
    ("", RuleOperator.starts_with, "YY66", False, ""),
]

# Not Starts With
cases += [
    ("YY66", RuleOperator.not_starts_with, "YY66", False, ""),
    ("YY66095", RuleOperator.not_starts_with, "YY66", False, ""),
    ("BB11", RuleOperator.not_starts_with, "YY66", True, ""),
    ("BYY66095", RuleOperator.not_starts_with, "YY66", True, ""),
    ("  YY66", RuleOperator.not_starts_with, "YY66", True, ""),
    (None, RuleOperator.not_starts_with, "YY66", True, ""),
    ("", RuleOperator.not_starts_with, "YY66", True, ""),
]

# Ends With
cases += [
    ("2BA", RuleOperator.ends_with, "2BA", True, ""),
    ("002BA", RuleOperator.ends_with, "2BA", True, ""),
    (None, RuleOperator.ends_with, "2BA", False, ""),
    ("", RuleOperator.ends_with, "2BA", False, ""),
    ("2BA00", RuleOperator.ends_with, "2BA", False, ""),
]

# is_in
cases += [
    ("", RuleOperator.is_in, "QH8,QJG", False, ""),
    (None, RuleOperator.is_in, "QH8,QJG", False, ""),
    ("AZ1", RuleOperator.is_in, "QH8,QJG", False, ""),
    ("QH8", RuleOperator.is_in, "QH8,QJG", True, ""),
]

# is not_in
cases += [
    ("", RuleOperator.not_in, "QH8,QJG", True, ""),
    (None, RuleOperator.not_in, "QH8,QJG", True, ""),
    ("AZ1", RuleOperator.not_in, "QH8,QJG", True, ""),
    ("QH8", RuleOperator.not_in, "QH8,QJG", False, ""),
]

# is member_of
cases += [
    ("cohort1,cohort2", RuleOperator.member_of, "cohort1", True, ""),
    (None, RuleOperator.member_of, "cohort1", False, ""),
    ("", RuleOperator.member_of, "cohort1", False, ""),
    ("cohort3", RuleOperator.member_of, "cohort1", False, ""),
]

# is not_member_of
cases += [
    ("cohort1,cohort2", RuleOperator.not_member_of, "cohort1", False, ""),
    (None, RuleOperator.not_member_of, "cohort1", True, ""),
    ("", RuleOperator.not_member_of, "cohort1", True, ""),
    ("cohort3", RuleOperator.not_member_of, "cohort1", True, ""),
]

# Day lesser than or equal to
cases += [
    ("20250426", RuleOperator.day_lte, "2", True, "Past date"),
    ("20250427", RuleOperator.day_lte, "2", True, "Present date"),
    ("20250428", RuleOperator.day_lte, "2", False, "Future date"),
    ("", RuleOperator.day_lte, "2", False, "Case empty string"),
    (None, RuleOperator.day_lte, "2", False, "Case None"),
]

# Day less than
cases += [
    ("20250426", RuleOperator.day_lt, "2", True, "Past date"),
    ("20250427", RuleOperator.day_lt, "2", False, "Present date"),
    ("20250428", RuleOperator.day_lt, "2", False, "Future date"),
]

# Day greater than or equal to
cases += [
    ("20250426", RuleOperator.day_gte, "2", False, "Past date"),
    ("20250427", RuleOperator.day_gte, "2", True, "Present date"),
    ("20250428", RuleOperator.day_gte, "2", True, "Future date"),
]

# Day greater than
cases += [
    ("20250426", RuleOperator.day_gt, "2", False, "Past date"),
    ("20250427", RuleOperator.day_gt, "2", False, "Present date"),
    ("20250428", RuleOperator.day_gt, "2", True, "Future date"),
]

# Week lesser than or equal to
cases += [
    ("20250502", RuleOperator.week_lte, 2, True, "Past week"),
    ("20250509", RuleOperator.week_lte, 2, True, "Present week"),
    ("20250516", RuleOperator.week_lte, 2, False, "Future week"),
]

# Week less than
cases += [
    ("20250502", RuleOperator.week_lt, 2, True, "Past week"),
    ("20250509", RuleOperator.week_lt, 2, False, "Present week"),
    ("20250516", RuleOperator.week_lt, 2, False, "Future week"),
]

# Week greater than or equal to
cases += [
    ("20250502", RuleOperator.week_gte, 2, False, "Past week"),
    ("20250509", RuleOperator.week_gte, 2, True, "Present week"),
    ("20250516", RuleOperator.week_gte, 2, True, "Future week"),
]

# Week greater than
cases += [
    ("20250502", RuleOperator.week_gt, 2, False, "Past week"),
    ("20250509", RuleOperator.week_gt, 2, False, "Present week"),
    ("20250516", RuleOperator.week_gt, 2, True, "Future week"),
]

# Year lesser than or equal to
cases += [
    ("20260425", RuleOperator.year_lte, 2, True, "Past year"),
    ("20270425", RuleOperator.year_lte, 2, True, "Present year"),
    ("20280425", RuleOperator.year_lte, 2, False, "Future year"),
]

# Year lesser than
cases += [
    ("20260425", RuleOperator.year_lt, 2, True, "Past year"),
    ("20270425", RuleOperator.year_lt, 2, False, "Present year"),
    ("20280425", RuleOperator.year_lt, 2, False, "Future year"),
]

# Year greater than or equal to
cases += [
    ("20260425", RuleOperator.year_gte, 2, False, "Past year"),
    ("20270425", RuleOperator.year_gte, 2, True, "Present year"),
    ("20280425", RuleOperator.year_gte, 2, True, "Future year"),
]

# Year greater than
cases += [
    ("20260425", RuleOperator.year_gt, 2, False, "Past year"),
    ("20270425", RuleOperator.year_gt, 2, False, "Present year"),
    ("20280425", RuleOperator.year_gt, 2, True, "Future year"),
]


@freeze_time("2025-04-25")
@pytest.mark.parametrize(("person_data", "rule_operator", "rule_value", "expected", "test_comment"), cases)
def test_operator(
    *,
    person_data: str | None,
    rule_operator: RuleOperator,
    rule_value: str | None,
    expected: bool,
    test_comment: str,
):
    # Given
    operator_class: type[Operator] = OperatorRegistry.get(rule_operator)
    operator: Operator = operator_class(rule_value=rule_value)

    # When
    actual = operator.matches(person_data)

    # Then
    assert_that(
        actual,
        equal_to(expected),
        f"{person_data!r} {rule_operator.name} {rule_value!r}{' - ' if test_comment else ''}{test_comment}",
    )
