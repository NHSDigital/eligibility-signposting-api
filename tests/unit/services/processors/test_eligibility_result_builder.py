import pytest
from hamcrest import assert_that, contains_inanyorder, is_

from eligibility_signposting_api.model.eligibility_status import (
    ActionCode,
    ActionDescription,
    ActionType,
    CohortGroupResult,
    ConditionName,
    InternalActionCode,
    IterationResult,
    Reason,
    RuleDescription,
    RuleName,
    RulePriority,
    RuleType,
    Status,
    SuggestedAction,
)
from eligibility_signposting_api.services.processors.eligibility_result_builder import EligibilityResultBuilder


@pytest.fixture
def result_builder():
    return EligibilityResultBuilder()


def test_build_condition_results_empty_input(result_builder):
    condition_results = {}
    result = result_builder.build_condition_results(condition_results)
    assert_that(result, is_([]))


def test_build_condition_results_single_condition_single_cohort_actionable(result_builder):
    cohort_group_results = [CohortGroupResult("COHORT_A", Status.actionable, [], "Cohort A Description", [])]
    suggested_actions = [
        SuggestedAction(
            internal_action_code=InternalActionCode("default_action_code"),
            action_type=ActionType("CareCardWithText"),
            action_code=ActionCode("BookLocal"),
            action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
            url_link=None,
            url_label=None,
        )
    ]
    iteration_result = IterationResult(Status.actionable, cohort_group_results, suggested_actions)

    condition_results = {ConditionName("RSV"): iteration_result}

    result = result_builder.build_condition_results(condition_results)

    assert_that(len(result), is_(1))
    assert_that(result[0].condition_name, is_(ConditionName("RSV")))
    assert_that(result[0].status, is_(Status.actionable))
    assert_that(result[0].actions, is_(suggested_actions))
    assert_that(result[0].status_text, is_(Status.actionable.get_status_text(ConditionName("RSV"))))

    assert_that(len(result[0].cohort_results), is_(1))
    deduplicated_cohort = result[0].cohort_results[0]
    assert_that(deduplicated_cohort.cohort_code, is_("COHORT_A"))
    assert_that(deduplicated_cohort.status, is_(Status.actionable))
    assert_that(deduplicated_cohort.reasons, is_([]))
    assert_that(deduplicated_cohort.description, is_("Cohort A Description"))
    assert_that(deduplicated_cohort.audit_rules, is_([]))


def test_build_condition_results_single_condition_single_cohort_not_eligible_with_reasons(result_builder):
    cohort_group_results = [CohortGroupResult("COHORT_A", Status.not_eligible, [], "Cohort A Description", [])]
    suggested_actions = [
        SuggestedAction(
            internal_action_code=InternalActionCode("default_action_code"),
            action_type=ActionType("CareCardWithText"),
            action_code=ActionCode("BookLocal"),
            action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
            url_link=None,
            url_label=None,
        )
    ]
    iteration_result = IterationResult(Status.not_eligible, cohort_group_results, suggested_actions)

    condition_results = {ConditionName("RSV"): iteration_result}

    result = result_builder.build_condition_results(condition_results)

    assert_that(len(result), is_(1))
    assert_that(result[0].condition_name, is_(ConditionName("RSV")))
    assert_that(result[0].status, is_(Status.not_eligible))
    assert_that(result[0].actions, is_(suggested_actions))
    assert_that(result[0].status_text, is_(Status.not_eligible.get_status_text(ConditionName("RSV"))))

    assert_that(len(result[0].cohort_results), is_(1))
    deduplicated_cohort = result[0].cohort_results[0]
    assert_that(deduplicated_cohort.cohort_code, is_("COHORT_A"))
    assert_that(deduplicated_cohort.status, is_(Status.not_eligible))
    assert_that(deduplicated_cohort.reasons, is_([]))
    assert_that(deduplicated_cohort.description, is_("Cohort A Description"))
    assert_that(deduplicated_cohort.audit_rules, is_([]))


def test_build_condition_results_single_condition_multiple_cohorts_same_cohort_code_same_status(result_builder):
    reason_1 = Reason(
        RuleType.filter,
        RuleName("Filter Rule 1"),
        RulePriority("1"),
        RuleDescription("Filter Rule Description 2"),
        matcher_matched=True,
    )
    reason_2 = Reason(
        RuleType.filter,
        RuleName("Filter Rule 2"),
        RulePriority("2"),
        RuleDescription("Filter Rule Description 2"),
        matcher_matched=True,
    )
    cohort_group_results = [
        CohortGroupResult("COHORT_A", Status.not_eligible, [reason_1], "", []),
        CohortGroupResult("COHORT_A", Status.not_eligible, [reason_2], "Cohort A Description 2", []),
        CohortGroupResult("COHORT_A", Status.not_eligible, [], "Cohort A Description 3", []),
    ]
    suggested_actions = [
        SuggestedAction(
            internal_action_code=InternalActionCode("default_action_code"),
            action_type=ActionType("CareCardWithText"),
            action_code=ActionCode("BookLocal"),
            action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
            url_link=None,
            url_label=None,
        )
    ]
    iteration_result = IterationResult(Status.not_eligible, cohort_group_results, suggested_actions)

    condition_results = {ConditionName("RSV"): iteration_result}

    result = result_builder.build_condition_results(condition_results)

    assert_that(len(result), is_(1))
    condition = result[0]
    assert_that(len(condition.cohort_results), is_(1))

    deduplicated_cohort = condition.cohort_results[0]
    assert_that(deduplicated_cohort.cohort_code, is_("COHORT_A"))
    assert_that(deduplicated_cohort.status, is_(Status.not_eligible))
    assert_that(deduplicated_cohort.reasons, contains_inanyorder(reason_1, reason_2))
    assert_that(deduplicated_cohort.description, is_("Cohort A Description 2"))
    assert_that(deduplicated_cohort.audit_rules, is_([]))


def test_build_condition_results_multiple_cohorts_different_cohort_code_same_status(result_builder):
    reason_1 = Reason(
        RuleType.filter,
        RuleName("Filter Rule 1"),
        RulePriority("1"),
        RuleDescription("Filter Rule Description 2"),
        matcher_matched=True,
    )
    reason_2 = Reason(
        RuleType.filter,
        RuleName("Filter Rule 2"),
        RulePriority("2"),
        RuleDescription("Filter Rule Description 2"),
        matcher_matched=True,
    )
    cohort_group_results = [
        CohortGroupResult("COHORT_X", Status.not_eligible, [reason_1], "Cohort X Description", []),
        CohortGroupResult("COHORT_Y", Status.not_eligible, [reason_2], "Cohort Y Description", []),
    ]
    suggested_actions = [
        SuggestedAction(
            internal_action_code=InternalActionCode("default_action_code"),
            action_type=ActionType("CareCardWithText"),
            action_code=ActionCode("BookLocal"),
            action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
            url_link=None,
            url_label=None,
        )
    ]
    iteration_result = IterationResult(Status.not_eligible, cohort_group_results, suggested_actions)

    condition_results = {ConditionName("RSV"): iteration_result}

    result = result_builder.build_condition_results(condition_results)

    assert_that(len(result), is_(1))
    condition = result[0]
    assert_that(len(condition.cohort_results), is_(2))

    expected_deduplicated_cohorts = [
        CohortGroupResult("COHORT_X", Status.not_eligible, [reason_1], "Cohort X Description", []),
        CohortGroupResult("COHORT_Y", Status.not_eligible, [reason_2], "Cohort Y Description", []),
    ]
    assert_that(condition.cohort_results, contains_inanyorder(*expected_deduplicated_cohorts))


def test_build_condition_results_cohorts_status_not_matching_iteration_status(result_builder):
    reason_1 = Reason(
        RuleType.filter, RuleName("Filter Rule 1"), RulePriority("1"), RuleDescription("Matching"), matcher_matched=True
    )
    reason_2 = Reason(
        RuleType.filter,
        RuleName("Filter Rule 2"),
        RulePriority("2"),
        RuleDescription("Not matching"),
        matcher_matched=True,
    )
    cohort_group_results = [
        CohortGroupResult("COHORT_X", Status.not_eligible, [reason_1], "Cohort X Description", []),
        CohortGroupResult("COHORT_Y", Status.not_actionable, [reason_2], "Cohort Y Description", []),
    ]

    iteration_result = IterationResult(Status.not_eligible, cohort_group_results, [])

    condition_results = {ConditionName("RSV"): iteration_result}

    result = result_builder.build_condition_results(condition_results)

    assert_that(len(result), is_(1))
    condition = result[0]
    assert_that(len(condition.cohort_results), is_(1))
    assert_that(condition.cohort_results[0].cohort_code, is_("COHORT_X"))
    assert_that(condition.cohort_results[0].status, is_(Status.not_eligible))


def test_build_condition_results_multiple_conditions(result_builder):
    reason_1 = Reason(
        RuleType.filter,
        RuleName("Filter Rule 1"),
        RulePriority("1"),
        RuleDescription("Filter Rule Description 2"),
        matcher_matched=True,
    )
    reason_2 = Reason(
        RuleType.filter,
        RuleName("Filter Rule 2"),
        RulePriority("2"),
        RuleDescription("Filter Rule Description 2"),
        matcher_matched=True,
    )
    cohort_group_result1 = [CohortGroupResult("RSV_COHORT", Status.not_eligible, [reason_1], "RSV Desc", [])]
    cohort_group_result2 = [CohortGroupResult("COVID_COHORT", Status.not_actionable, [reason_2], "Covid Desc", [])]

    iteration_result1 = IterationResult(Status.not_eligible, cohort_group_result1, [])

    iteration_result2 = IterationResult(Status.not_actionable, cohort_group_result2, [])

    condition_results = {
        ConditionName("RSV"): iteration_result1,
        ConditionName("COVID"): iteration_result2,
    }

    result = result_builder.build_condition_results(condition_results)

    rsv = next((c for c in result if c.condition_name == ConditionName("RSV")), None)
    assert_that(rsv.status, is_(Status.not_eligible))
    assert_that(len(rsv.cohort_results), is_(1))
    assert_that(rsv.cohort_results[0].cohort_code, is_("RSV_COHORT"))
    assert_that(rsv.cohort_results[0].reasons, is_([reason_1]))

    covid = next((c for c in result if c.condition_name == ConditionName("COVID")), None)
    assert_that(covid.status, is_(Status.not_actionable))
    assert_that(len(covid.cohort_results), is_(1))
    assert_that(covid.cohort_results[0].cohort_code, is_("COVID_COHORT"))
    assert_that(covid.cohort_results[0].reasons, is_([reason_2]))
