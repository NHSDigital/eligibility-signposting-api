from hamcrest import assert_that, has_properties

from eligibility_signposting_api.model.campaign_config import RuleName, RulePriority
from eligibility_signposting_api.model.eligibility_status import (
    ConditionName,
    MatchedActionDetail,
    RuleType,
    Status,
    StatusText,
    SuggestedAction,
)


class TestStatus:
    def test_ordering(self):
        assert Status.not_eligible < Status.not_actionable
        assert Status.not_actionable < Status.actionable
        assert Status.actionable > Status.not_actionable
        assert Status.not_actionable > Status.not_eligible
        assert Status.not_eligible == Status.not_eligible

    def test_is_exclusion(self):
        assert Status.not_eligible.is_exclusion
        assert Status.not_actionable.is_exclusion
        assert not Status.actionable.is_exclusion

    def test_worst_status(self):
        assert Status.worst(Status.not_eligible, Status.actionable) == Status.not_eligible
        assert Status.worst(Status.actionable, Status.not_actionable) == Status.not_actionable
        assert Status.worst(Status.not_eligible, Status.not_actionable, Status.actionable) == Status.not_eligible
        assert Status.worst(Status.actionable) == Status.actionable

    def test_best_status(self):
        assert Status.best(Status.not_eligible, Status.actionable) == Status.actionable
        assert Status.best(Status.actionable, Status.not_actionable) == Status.actionable
        assert Status.best(Status.not_eligible, Status.not_actionable, Status.actionable) == Status.actionable
        assert Status.best(Status.not_eligible) == Status.not_eligible

    def test_get_status_text(self):
        assert Status.not_eligible.get_default_status_text(ConditionName("COVID")) == StatusText(
            "We do not believe you can have it"
        )

        assert Status.not_actionable.get_default_status_text(ConditionName("FLU")) == StatusText(
            "You should have the FLU vaccine"
        )

        assert Status.actionable.get_default_status_text(ConditionName("COVID")) == StatusText(
            "You should have the COVID vaccine"
        )

    def test_get_action_rule_type(self):
        assert Status.not_eligible.get_action_rule_type() == RuleType(RuleType.not_eligible_actions)

        assert Status.not_actionable.get_action_rule_type() == RuleType(RuleType.not_actionable_actions)

        assert Status.actionable.get_action_rule_type() == RuleType(RuleType.redirect)


def test_matched_action_detail_default_status_text_override_is_none():
    action_detail = MatchedActionDetail()

    assert_that(action_detail, has_properties(status_text_override=None))


def test_matched_action_detail_stores_status_text_override_value():
    action_detail = MatchedActionDetail(status_text_override=StatusText("X"))

    assert_that(action_detail, has_properties(status_text_override=StatusText("X")))


def test_matched_action_detail_existing_constructor_still_works_with_three_args():
    actions: list[SuggestedAction] = []

    action_detail = MatchedActionDetail(RuleName("RuleA"), RulePriority(1), actions)

    assert_that(
        action_detail,
        has_properties(
            rule_name=RuleName("RuleA"),
            rule_priority=RulePriority(1),
            actions=actions,
            status_text_override=StatusText(None),
        ),
    )


def test_matched_action_detail_existing_constructor_works_with_four_args():
    actions: list[SuggestedAction] = []

    action_detail = MatchedActionDetail(
        RuleName("RuleA"), RulePriority(1), actions, status_text_override=StatusText("Override")
    )

    assert_that(
        action_detail,
        has_properties(
            rule_name=RuleName("RuleA"),
            rule_priority=RulePriority(1),
            actions=actions,
            status_text_override=StatusText("Override"),
        ),
    )
