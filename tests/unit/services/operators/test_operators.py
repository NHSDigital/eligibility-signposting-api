import pytest
from freezegun import freeze_time

from eligibility_signposting_api.model.rules import RuleOperator
from eligibility_signposting_api.services.rules.operators import AttributeData, Operator, OperatorRegistry

cases: list[tuple[RuleOperator, AttributeData, AttributeData, bool]] = [
    # Equals
    (RuleOperator.equals, "42", "42", True),
    (RuleOperator.equals, "42", "", False),
    (RuleOperator.equals, "42", None, False),
    (RuleOperator.equals, "42", "99", False),
    (RuleOperator.equals, "-1", "-1", True),
    (RuleOperator.equals, "-1", "0", False),
    (RuleOperator.equals, "-1", "", False),
    (RuleOperator.equals, "-1", None, False),
    (RuleOperator.equals, "", "", False),
    (RuleOperator.equals, "", None, False),
    (RuleOperator.equals, None, "", False),
    (RuleOperator.equals, None, None, False),
    (RuleOperator.equals, "42", "Fourtytwo", False),
    # Greater Than
    (RuleOperator.gt, "100", "101", True),
    (RuleOperator.gt, "100", "100", False),
    (RuleOperator.gt, "100", "99", False),
    (RuleOperator.gt, "100", "", False),
    (RuleOperator.gt, "100", None, False),
    (RuleOperator.gt, "-1", "0", True),
    (RuleOperator.gt, "-1", "-1", False),
    (RuleOperator.gt, "-1", "-2", False),
    (RuleOperator.gt, "-1", "", False),
    (RuleOperator.gt, "-1", None, False),
    # Less Than
    (RuleOperator.lt, "100", "42", True),
    (RuleOperator.lt, "100", "99", True),
    (RuleOperator.lt, "100", "100", False),
    (RuleOperator.lt, "100", "101", False),
    (RuleOperator.lt, "100", "", False),
    (RuleOperator.lt, "100", None, False),
    (RuleOperator.lt, "-1", "-2", True),
    (RuleOperator.lt, "-1", "-1", False),
    (RuleOperator.lt, "-1", "0", False),
    (RuleOperator.lt, "-1", "", False),
    (RuleOperator.lt, "-1", None, False),
    # Not Equals
    (RuleOperator.ne, "27", "98", True),
    (RuleOperator.ne, "27", "", False),
    (RuleOperator.ne, "27", None, False),
    (RuleOperator.ne, "27", "27", False),
    (RuleOperator.ne, "-1", "-1", False),
    (RuleOperator.ne, "-1", "0", True),
    (RuleOperator.ne, "-1", "", False),
    (RuleOperator.ne, "-1", None, False),
    # Greater Than or Equal
    (RuleOperator.gte, "100", "100", True),
    (RuleOperator.gte, "100", "101", True),
    (RuleOperator.gte, "100", "99", False),
    (RuleOperator.gte, "100", "", False),
    (RuleOperator.gte, "100", None, False),
    (RuleOperator.gte, "-1", "0", True),
    (RuleOperator.gte, "-1", "-1", True),
    (RuleOperator.gte, "-1", "-2", False),
    (RuleOperator.gte, "-1", "", False),
    (RuleOperator.gte, "-1", None, False),
    # Less Than or Equal
    (RuleOperator.lte, "100", "99", True),
    (RuleOperator.lte, "100", "100", True),
    (RuleOperator.lte, "100", "101", False),
    (RuleOperator.lte, "100", "", False),
    (RuleOperator.lte, "100", None, False),
    (RuleOperator.lte, "-1", "-2", True),
    (RuleOperator.lte, "-1", "-1", True),
    (RuleOperator.lte, "-1", "0", False),
    (RuleOperator.lte, "-1", "", False),
    (RuleOperator.lte, "-1", None, False),
    # Is Null
    (RuleOperator.is_null, None, "", True),
    (RuleOperator.is_null, None, None, True),
    (RuleOperator.is_null, None, "email_flag", False),
    (RuleOperator.is_null, None, 42, False),
    # Is Not Null
    (RuleOperator.is_not_null, None, "", False),
    (RuleOperator.is_not_null, None, None, False),
    (RuleOperator.is_not_null, None, "email_flag", True),
    (RuleOperator.is_not_null, None, 42, True),
    # Between - inclusive
    (RuleOperator.between, "1,3", "0", False),
    (RuleOperator.between, "1,3", "1", True),
    (RuleOperator.between, "1,3", "2", True),
    (RuleOperator.between, "1,3", "3", True),
    (RuleOperator.between, "1,3", "4", False),
    (RuleOperator.between, "1,3", "", False),
    (RuleOperator.between, "1,3", None, False),
    (RuleOperator.between, "3,1", "0", False),
    (RuleOperator.between, "3,1", "1", True),
    (RuleOperator.between, "3,1", "2", True),
    (RuleOperator.between, "3,1", "3", True),
    (RuleOperator.between, "3,1", "4", False),
    (RuleOperator.between, "3,1", "", False),
    (RuleOperator.between, "3,1", None, False),
    (RuleOperator.between, "3,3", "2", False),
    (RuleOperator.between, "3,3", "3", True),
    (RuleOperator.between, "3,3", "4", False),
    (RuleOperator.between, "3,3", "", False),
    (RuleOperator.between, "3,3", None, False),
    (RuleOperator.between, "20100302,20100304", "20100301", False),
    (RuleOperator.between, "20100302,20100304", "20100302", True),
    (RuleOperator.between, "20100302,20100304", "20100303", True),
    (RuleOperator.between, "20100302,20100304", "20100304", True),
    (RuleOperator.between, "20100302,20100304", "20100305", False),
    (RuleOperator.between, "20100302,20100304", "", False),
    (RuleOperator.between, "20100302,20100304", None, False),
    # Not Between
    (RuleOperator.not_between, "1,3", "0", True),
    (RuleOperator.not_between, "1,3", "1", False),
    (RuleOperator.not_between, "1,3", "2", False),
    (RuleOperator.not_between, "1,3", "3", False),
    (RuleOperator.not_between, "1,3", "4", True),
    (RuleOperator.not_between, "1,3", "", False),
    (RuleOperator.not_between, "1,3", None, False),
    (RuleOperator.not_between, "3,1", "0", True),
    (RuleOperator.not_between, "3,1", "1", False),
    (RuleOperator.not_between, "3,1", "2", False),
    (RuleOperator.not_between, "3,1", "3", False),
    (RuleOperator.not_between, "3,1", "4", True),
    (RuleOperator.not_between, "3,1", "", False),
    (RuleOperator.not_between, "3,1", None, False),
    (RuleOperator.not_between, "3,3", "2", True),
    (RuleOperator.not_between, "3,3", "3", False),
    (RuleOperator.not_between, "3,3", "4", True),
    (RuleOperator.not_between, "3,3", "", False),
    (RuleOperator.not_between, "3,3", None, False),
    # Is Empty
    (RuleOperator.is_empty, None, "", True),
    (RuleOperator.is_empty, None, ",", True),
    (RuleOperator.is_empty, None, ",,,,", True),
    (RuleOperator.is_empty, None, ", , , ,", True),
    (RuleOperator.is_empty, None, "  ,  ,  ,  ,  ", True),
    (RuleOperator.is_empty, None, None, True),
    (RuleOperator.is_empty, None, "              ", True),
    (RuleOperator.is_empty, None, "a", False),
    (RuleOperator.is_empty, None, "this is not empty", False),
    (RuleOperator.is_empty, None, "a,", False),
    (RuleOperator.is_empty, None, ",a", False),
    (RuleOperator.is_empty, None, "a,b,c", False),
    # Is Not Empty
    (RuleOperator.is_not_empty, None, "a", True),
    (RuleOperator.is_not_empty, None, "this is not empty", True),
    (RuleOperator.is_not_empty, None, "a,", True),
    (RuleOperator.is_not_empty, None, ",a", True),
    (RuleOperator.is_not_empty, None, "a,b,c", True),
    (RuleOperator.is_not_empty, None, "", False),
    (RuleOperator.is_not_empty, None, ",", False),
    (RuleOperator.is_not_empty, None, ",,,,", False),
    (RuleOperator.is_not_empty, None, ", , , ,", False),
    (RuleOperator.is_not_empty, None, "  ,  ,  ,  ,  ", False),
    (RuleOperator.is_not_empty, None, None, False),
    (RuleOperator.is_not_empty, None, "              ", False),
    # Is True
    (RuleOperator.is_true, None, True, True),
    (RuleOperator.is_true, None, False, False),
    (RuleOperator.is_true, None, "", False),
    (RuleOperator.is_true, None, None, False),
    (RuleOperator.is_true, None, "True", False),
    # Is False
    (RuleOperator.is_false, None, False, True),
    (RuleOperator.is_false, None, True, False),
    (RuleOperator.is_false, None, "", False),
    (RuleOperator.is_false, None, None, False),
    (RuleOperator.is_false, None, "False", False),
    # Has it contains
    (RuleOperator.contains, "A12", "A12 3DC", True),
    (RuleOperator.contains, "A12", "A12", True),
    (RuleOperator.contains, "A12", None, False),
    (RuleOperator.contains, "A12", "", False),
    (RuleOperator.contains, "A12", "A23", False),
    (RuleOperator.contains, "A12", 23, False),
    # Has it not_contains
    (RuleOperator.not_contains, "A12", "A22", True),
    (RuleOperator.not_contains, "A12", None, True),
    (RuleOperator.not_contains, "A12", "", True),
    (RuleOperator.not_contains, "A12", 23, True),
    (RuleOperator.not_contains, "A12", "A12", False),
    # Does it starts_with
    (RuleOperator.starts_with, "YY66", "YY66", True),
    (RuleOperator.starts_with, "YY66", "YY66095", True),
    (RuleOperator.starts_with, "YY66", "BB11", False),
    (RuleOperator.starts_with, "YY66", "BYY66095", False),
    (RuleOperator.starts_with, "YY66", "  YY66", False),
    (RuleOperator.starts_with, "YY66", None, False),
    (RuleOperator.starts_with, "YY66", "", False),
    # Does it not_starts_with
    (RuleOperator.not_starts_with, "YY66", "YY66", False),
    (RuleOperator.not_starts_with, "YY66", "YY66095", False),
    (RuleOperator.not_starts_with, "YY66", "BB11", True),
    (RuleOperator.not_starts_with, "YY66", "BYY66095", True),
    (RuleOperator.not_starts_with, "YY66", "  YY66", True),
    (RuleOperator.not_starts_with, "YY66", None, True),
    (RuleOperator.not_starts_with, "YY66", "", True),
    # Does it ends_with
    (RuleOperator.ends_with, "2BA", "2BA", True),
    (RuleOperator.ends_with, "2BA", "002BA", True),
    (RuleOperator.ends_with, "2BA", None, False),
    (RuleOperator.ends_with, "2BA", "", False),
    (RuleOperator.ends_with, "2BA", "2BA00", False),
    # is_in
    (RuleOperator.is_in, "QH8,QJG", "", False),
    (RuleOperator.is_in, "QH8,QJG", None, False),
    (RuleOperator.is_in, "QH8,QJG", "AZ1", False),
    (RuleOperator.is_in, "QH8,QJG", "QH8", True),
    # is not_in
    (RuleOperator.not_in, "QH8,QJG", "", True),
    (RuleOperator.not_in, "QH8,QJG", None, True),
    (RuleOperator.not_in, "QH8,QJG", "AZ1", True),
    (RuleOperator.not_in, "QH8,QJG", "QH8", False),
    # is member_of
    (RuleOperator.member_of, "cohort1", "cohort1,cohort2", True),
    (RuleOperator.member_of, "cohort1", None, False),
    (RuleOperator.member_of, "cohort1", "", False),
    (RuleOperator.member_of, "cohort1", "cohort3", False),
    # is not_member_of
    (RuleOperator.not_member_of, "cohort1", "cohort1,cohort2", False),
    (RuleOperator.not_member_of, "cohort1", None, True),
    (RuleOperator.not_member_of, "cohort1", "", True),
    (RuleOperator.not_member_of, "cohort1", "cohort3", True),
    # Day lesser than or equal to
    (RuleOperator.day_lte, "2", "20250426", True),  # Past date
    (RuleOperator.day_lte, "2", "20250427", True),  # Present date
    (RuleOperator.day_lte, "2", "20250428", False),  # Future date
    (RuleOperator.day_lte, "2", "", False),  # Case empty string: behaves the same for all the date operators
    (RuleOperator.day_lte, "2", None, False),  # Case None: behaves the same for all the date operators
    # Day less than
    (RuleOperator.day_lt, "2", "20250426", True),  # Past date
    (RuleOperator.day_lt, "2", "20250427", False),  # Present date
    (RuleOperator.day_lt, "2", "20250428", False),  # Future date
    # Day greater than or equal to
    (RuleOperator.day_gte, "2", "20250426", False),  # Past date
    (RuleOperator.day_gte, "2", "20250427", True),  # Present date
    (RuleOperator.day_gte, "2", "20250428", True),  # Future date
    # Day greater than
    (RuleOperator.day_gt, "2", "20250426", False),  # Past date
    (RuleOperator.day_gt, "2", "20250427", False),  # Present date
    (RuleOperator.day_gt, "2", "20250428", True),  # Future date
    # Week lesser than or equal to
    (RuleOperator.week_lte, 2, "20250502", True),  # Past week
    (RuleOperator.week_lte, 2, "20250509", True),  # Present week
    (RuleOperator.week_lte, 2, "20250516", False),  # Future week
    # Week less than
    (RuleOperator.week_lt, 2, "20250502", True),  # Past week
    (RuleOperator.week_lt, 2, "20250509", False),  # Present week
    (RuleOperator.week_lt, 2, "20250516", False),  # Future week
    # Week greater than or equal to
    (RuleOperator.week_gte, 2, "20250502", False),  # Past week
    (RuleOperator.week_gte, 2, "20250509", True),  # Present week
    (RuleOperator.week_gte, 2, "20250516", True),  # Future week
    # Week greater than
    (RuleOperator.week_gt, 2, "20250502", False),  # Past week
    (RuleOperator.week_gt, 2, "20250509", False),  # Present week
    (RuleOperator.week_gt, 2, "20250516", True),  # Future week
    # Year lesser than or equal to
    (RuleOperator.year_lte, 2, "20260425", True),  # Past year
    (RuleOperator.year_lte, 2, "20270425", True),  # Present year
    (RuleOperator.year_lte, 2, "20280425", False),  # Future year
    # Year lesser than
    (RuleOperator.year_lt, 2, "20260425", True),  # Past year
    (RuleOperator.year_lt, 2, "20270425", False),  # Present year
    (RuleOperator.year_lt, 2, "20280425", False),  # Future year
    # Year greater than or equal to
    (RuleOperator.year_gte, 2, "20260425", False),  # Past year
    (RuleOperator.year_gte, 2, "20270425", True),  # Present year
    (RuleOperator.year_gte, 2, "20280425", True),  # Future year
    # Year greater than
    (RuleOperator.year_gt, 2, "20260425", False),  # Past year
    (RuleOperator.year_gt, 2, "20270425", False),  # Present year
    (RuleOperator.year_gt, 2, "20280425", True),  # Future year
]


@freeze_time("2025-04-25")
@pytest.mark.parametrize(("rule_operator", "rule_value", "person_data", "expected"), cases)
def test_operator(rule_operator: RuleOperator, rule_value: AttributeData, person_data: AttributeData, expected: bool):  # noqa: FBT001
    # Given
    operator_class: type[Operator] = OperatorRegistry.get(rule_operator)
    operator: Operator = operator_class(rule_value=rule_value)

    # When
    actual = operator.matches(person_data)

    # Then
    assert actual is expected
