from eligibility_signposting_api.model.eligibility_status import ConditionName, RuleType, Status, StatusText


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
