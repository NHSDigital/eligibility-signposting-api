from unittest.mock import Mock, call, patch

import pytest
from hamcrest import assert_that, is_
from pydantic import HttpUrl

from eligibility_signposting_api.model.campaign_config import AvailableAction, RuleName, RulePriority, RuleType
from eligibility_signposting_api.model.eligibility_status import (
    ActionCode,
    ActionDescription,
    ActionType,
    InternalActionCode,
    Status,
    SuggestedAction,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.action_rule_handler import ActionRuleHandler
from tests.fixtures.builders.model import rule as rule_builder
from tests.fixtures.builders.model.rule import ActionsMapperFactory


@pytest.fixture
def action_rule_handler():
    return ActionRuleHandler()


MOCK_PERSON = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"}])

BOOK_NBS_COMMS = AvailableAction(
    ActionType="ButtonAuthLink",
    ExternalRoutingCode="BookNBS",
    ActionDescription="Action description",
    UrlLink=HttpUrl("https://www.nhs.uk/book-rsv"),
    UrlLabel="Continue to booking",
)

DEFAULT_COMMS_DETAIL = AvailableAction(
    ActionType="CareCardWithText",
    ExternalRoutingCode="BookLocal",
    ActionDescription="You can get an RSV vaccination at your GP surgery",
)


def test_get_action_rules_components_redirect_type():
    iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_redirect",
        default_not_eligible_routing="default_not_eligible",
        default_not_actionable_routing="default_not_actionable",
        actions_mapper=ActionsMapperFactory.build(),
        iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(name="RedirectRule")],
    )
    rules_found, mapper, default_comms = ActionRuleHandler.get_action_rules_components(iteration, RuleType.redirect)
    assert_that(len(rules_found), is_(1))
    assert_that(rules_found[0].name, is_(RuleName("RedirectRule")))
    assert_that(mapper, is_(iteration.actions_mapper))
    assert_that(default_comms, is_("default_redirect"))


def test_get_action_rules_components_not_eligible_actions_type():
    iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_redirect",
        default_not_eligible_routing="default_not_eligible",
        default_not_actionable_routing="default_not_actionable",
        actions_mapper=ActionsMapperFactory.build(),
        iteration_rules=[rule_builder.ICBNonEligibleActionRuleFactory.build(name="NonEligibleRule")],
    )
    rules_found, mapper, default_comms = ActionRuleHandler.get_action_rules_components(
        iteration, RuleType.not_eligible_actions
    )
    assert_that(len(rules_found), is_(1))
    assert_that(rules_found[0].name, is_(RuleName("NonEligibleRule")))
    assert_that(mapper, is_(iteration.actions_mapper))
    assert_that(default_comms, is_("default_not_eligible"))


def test_get_action_rules_components_no_matching_rules():
    iteration = rule_builder.IterationFactory.build(
        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()]
    )
    rules_found, _, _ = ActionRuleHandler.get_action_rules_components(iteration, RuleType.redirect)
    assert_that(len(rules_found), is_(0))


def test_get_actions_from_comms_single_comm():
    action_mapper = ActionsMapperFactory.build(root={"book_nbs": BOOK_NBS_COMMS})
    actions = ActionRuleHandler.get_actions_from_comms(action_mapper, "book_nbs")
    assert_that(len(actions), is_(1))
    assert_that(actions[0].internal_action_code, is_(InternalActionCode("book_nbs")))
    assert_that(actions[0].action_code, is_(ActionCode("BookNBS")))


def test_get_actions_from_comms_multiple_comms():
    action_mapper = ActionsMapperFactory.build(root={"book_nbs": BOOK_NBS_COMMS, "default_comms": DEFAULT_COMMS_DETAIL})
    actions = ActionRuleHandler.get_actions_from_comms(action_mapper, "book_nbs|default_comms")
    assert_that(len(actions), is_(2))
    assert_that(actions[0].internal_action_code, is_(InternalActionCode("book_nbs")))
    assert_that(actions[1].internal_action_code, is_(InternalActionCode("default_comms")))


def test_get_actions_from_comms_unknown_comm_code():
    action_mapper = ActionsMapperFactory.build(root={"book_nbs": BOOK_NBS_COMMS})
    actions = ActionRuleHandler.get_actions_from_comms(action_mapper, "book_nbs|unknown_code")
    assert_that(len(actions), is_(1))
    assert_that(actions[0].internal_action_code, is_(InternalActionCode("book_nbs")))


def test_get_actions_from_comms_empty_string():
    action_mapper = ActionsMapperFactory.build(root={"book_nbs": BOOK_NBS_COMMS})
    actions = ActionRuleHandler.get_actions_from_comms(action_mapper, "")
    assert_that(len(actions), is_(0))


def test_get_actions_from_comms_no_actions_found():
    action_mapper = ActionsMapperFactory.build(root={})
    actions = ActionRuleHandler.get_actions_from_comms(action_mapper, "unknown_code")
    assert_that(len(actions), is_(0))


@patch("eligibility_signposting_api.services.calculators.rule_calculator.RuleCalculator")
@patch.object(ActionRuleHandler, "get_actions_from_comms")
@patch.object(ActionRuleHandler, "get_action_rules_components")
def test_handle_actions_no_matching_rules_returns_default(
    mock_get_action_rules_components,
    mock_get_actions_from_comms,
    mock_rule_calculator_class,
    action_rule_handler: ActionRuleHandler,
):
    active_iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_action_code",
        actions_mapper=ActionsMapperFactory.build(root={"default_action_code": DEFAULT_COMMS_DETAIL}),
        iteration_rules=[],
    )

    mock_get_action_rules_components.return_value = (
        [],
        active_iteration.actions_mapper,
        active_iteration.default_comms_routing,
    )

    mock_get_actions_from_comms.side_effect = [
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType(DEFAULT_COMMS_DETAIL.action_type),
                action_code=ActionCode(DEFAULT_COMMS_DETAIL.action_code),
                action_description=ActionDescription(DEFAULT_COMMS_DETAIL.action_description),
                url_link=DEFAULT_COMMS_DETAIL.url_link,
                url_label=DEFAULT_COMMS_DETAIL.url_label,
            )
        ],
        [],
    ]

    matched_action_detail = action_rule_handler.handle(MOCK_PERSON, active_iteration, RuleType.redirect)

    assert_that(len(matched_action_detail.actions), is_(1))
    assert_that(matched_action_detail.actions[0].internal_action_code, is_(InternalActionCode("default_action_code")))
    assert_that(matched_action_detail.rule_priority, is_(None))
    assert_that(matched_action_detail.rule_name, is_(None))
    mock_get_action_rules_components.assert_called_once_with(active_iteration, RuleType.redirect)
    mock_get_actions_from_comms.assert_called_once_with(active_iteration.actions_mapper, "default_action_code")
    mock_rule_calculator_class.assert_not_called()


@patch("eligibility_signposting_api.services.processors.action_rule_handler.RuleCalculator")
@patch.object(ActionRuleHandler, "get_actions_from_comms")
@patch.object(ActionRuleHandler, "get_action_rules_components")
def test_handle_actions_matching_rule_overrides_default(
    mock_get_action_rules_components,
    mock_get_actions_from_comms,
    mock_rule_calculator_class,
    action_rule_handler: ActionRuleHandler,
):
    matching_rule = rule_builder.ICBRedirectRuleFactory.build(
        priority=10, comms_routing="rule_specific_action", name="RuleSpecificAction"
    )
    active_iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_action_code",
        actions_mapper=ActionsMapperFactory.build(
            root={"default_action_code": DEFAULT_COMMS_DETAIL, "rule_specific_action": BOOK_NBS_COMMS}
        ),
        iteration_rules=[matching_rule],
    )
    mock_get_action_rules_components.return_value = (
        (matching_rule,),
        active_iteration.actions_mapper,
        active_iteration.default_comms_routing,
    )

    mock_get_actions_from_comms.side_effect = [
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType(DEFAULT_COMMS_DETAIL.action_type),
                action_code=ActionCode(DEFAULT_COMMS_DETAIL.action_code),
                action_description=ActionDescription(DEFAULT_COMMS_DETAIL.action_description),
                url_link=DEFAULT_COMMS_DETAIL.url_link,
                url_label=DEFAULT_COMMS_DETAIL.url_label,
            )
        ],
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("rule_specific_action"),
                action_type=ActionType(BOOK_NBS_COMMS.action_type),
                action_code=ActionCode(BOOK_NBS_COMMS.action_code),
                action_description=ActionDescription(BOOK_NBS_COMMS.action_description),
                url_link=BOOK_NBS_COMMS.url_link,
                url_label=BOOK_NBS_COMMS.url_label,
            )
        ],
    ]

    mock_rule_instance = Mock()
    mock_rule_instance.evaluate_exclusion.return_value = (Status.actionable, Mock(matcher_matched=True))
    mock_rule_calculator_class.return_value = mock_rule_instance

    matched_action_detail = action_rule_handler.handle(MOCK_PERSON, active_iteration, RuleType.redirect)

    assert_that(len(matched_action_detail.actions), is_(1))
    assert_that(matched_action_detail.actions[0].internal_action_code, is_(InternalActionCode("rule_specific_action")))
    assert_that(matched_action_detail.rule_priority, is_(RulePriority(10)))
    assert_that(matched_action_detail.rule_name, is_(RuleName("RuleSpecificAction")))

    mock_get_action_rules_components.assert_called_once_with(active_iteration, RuleType.redirect)
    assert_that(mock_get_actions_from_comms.call_count, is_(2))
    mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "default_action_code")
    mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "rule_specific_action")
    mock_rule_calculator_class.assert_called_once_with(person=MOCK_PERSON, rule=matching_rule)


@patch("eligibility_signposting_api.services.processors.action_rule_handler.RuleCalculator")
@patch.object(ActionRuleHandler, "get_actions_from_comms")
@patch.object(ActionRuleHandler, "get_action_rules_components")
def test_handle_rule_mismatch_returns_default(
    mock_get_action_rules_components,
    mock_get_actions_from_comms,
    mock_rule_calculator_class,
    action_rule_handler: ActionRuleHandler,
):
    mismatching_rule = rule_builder.ICBRedirectRuleFactory.build(
        priority=10, comms_routing="rule_specific_action", name="RuleSpecificAction"
    )
    active_iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_action_code",
        actions_mapper=ActionsMapperFactory.build(
            root={"default_action_code": DEFAULT_COMMS_DETAIL, "rule_specific_action": BOOK_NBS_COMMS}
        ),
        iteration_rules=[mismatching_rule],
    )
    rule_type = RuleType.redirect

    mock_get_action_rules_components.return_value = (
        (mismatching_rule,),
        active_iteration.actions_mapper,
        active_iteration.default_comms_routing,
    )

    mock_get_actions_from_comms.side_effect = [
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType(DEFAULT_COMMS_DETAIL.action_type),
                action_code=ActionCode(DEFAULT_COMMS_DETAIL.action_code),
                action_description=ActionDescription(DEFAULT_COMMS_DETAIL.action_description),
                url_link=DEFAULT_COMMS_DETAIL.url_link,
                url_label=DEFAULT_COMMS_DETAIL.url_label,
            )
        ],
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("rule_specific_action"),
                action_type=ActionType(BOOK_NBS_COMMS.action_type),
                action_code=ActionCode(BOOK_NBS_COMMS.action_code),
                action_description=ActionDescription(BOOK_NBS_COMMS.action_description),
                url_link=BOOK_NBS_COMMS.url_link,
                url_label=BOOK_NBS_COMMS.url_label,
            )
        ],
    ]

    mock_rule_calculator_class.return_value.evaluate_exclusion.return_value = (
        Status.actionable,
        Mock(matcher_matched=False),
    )

    matched_action_detail = action_rule_handler.handle(MOCK_PERSON, active_iteration, rule_type)

    assert_that(len(matched_action_detail.actions), is_(1))
    assert_that(matched_action_detail.actions[0].internal_action_code, is_(InternalActionCode("default_action_code")))
    assert_that(matched_action_detail.rule_priority, is_(None))
    assert_that(matched_action_detail.rule_name, is_(None))

    mock_get_action_rules_components.assert_called_once_with(active_iteration, rule_type)
    assert_that(mock_get_actions_from_comms.call_count, is_(1))
    mock_get_actions_from_comms.assert_called_once_with(active_iteration.actions_mapper, "default_action_code")
    mock_rule_calculator_class.assert_called_once_with(person=MOCK_PERSON, rule=mismatching_rule)


@patch("eligibility_signposting_api.services.processors.action_rule_handler.RuleCalculator")
@patch.object(ActionRuleHandler, "get_actions_from_comms")
@patch.object(ActionRuleHandler, "get_action_rules_components")
def test_handle_multiple_rules_same_priority_all_match(
    mock_get_action_rules_components,
    mock_get_actions_from_comms,
    mock_rule_calculator_class,
    action_rule_handler: ActionRuleHandler,
):
    rule1 = rule_builder.ICBRedirectRuleFactory.build(priority=10, comms_routing="action_a", name="RuleA")
    rule2 = rule_builder.ICBRedirectRuleFactory.build(priority=10, comms_routing="action_b", name="RuleB")
    active_iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_action_code",
        actions_mapper=ActionsMapperFactory.build(
            root={
                "default_action_code": DEFAULT_COMMS_DETAIL,
                "action_a": BOOK_NBS_COMMS,
                "action_b": DEFAULT_COMMS_DETAIL,
            }
        ),
        iteration_rules=[rule1, rule2],
    )

    mock_get_action_rules_components.return_value = (
        (rule1, rule2),
        active_iteration.actions_mapper,
        active_iteration.default_comms_routing,
    )

    mock_get_actions_from_comms.side_effect = [
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType(DEFAULT_COMMS_DETAIL.action_type),
                action_code=ActionCode(DEFAULT_COMMS_DETAIL.action_code),
                action_description=ActionDescription(DEFAULT_COMMS_DETAIL.action_description),
                url_link=DEFAULT_COMMS_DETAIL.url_link,
                url_label=DEFAULT_COMMS_DETAIL.url_label,
            )
        ],
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("action_a"),
                action_type=ActionType(BOOK_NBS_COMMS.action_type),
                action_code=ActionCode(BOOK_NBS_COMMS.action_code),
                action_description=ActionDescription(BOOK_NBS_COMMS.action_description),
                url_link=BOOK_NBS_COMMS.url_link,
                url_label=BOOK_NBS_COMMS.url_label,
            )
        ],
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("action_b"),
                action_type=ActionType(DEFAULT_COMMS_DETAIL.action_type),
                action_code=ActionCode(DEFAULT_COMMS_DETAIL.action_code),
                action_description=ActionDescription(DEFAULT_COMMS_DETAIL.action_description),
                url_link=DEFAULT_COMMS_DETAIL.url_link,
                url_label=DEFAULT_COMMS_DETAIL.url_label,
            )
        ],
    ]

    mock_rule_calculator_class.side_effect = [
        Mock(evaluate_exclusion=Mock(return_value=(Status.actionable, Mock(matcher_matched=True)))),
        Mock(evaluate_exclusion=Mock(return_value=(Status.actionable, Mock(matcher_matched=True)))),
    ]

    matched_action_detail = action_rule_handler.handle(MOCK_PERSON, active_iteration, RuleType.redirect)

    assert_that(len(matched_action_detail.actions), is_(1))
    assert_that(matched_action_detail.actions[0].internal_action_code, is_(InternalActionCode("action_a")))
    assert_that(matched_action_detail.rule_priority, is_(RulePriority(10)))
    assert_that(matched_action_detail.rule_name, is_(RuleName("RuleA")))

    assert_that(mock_rule_calculator_class.call_count, is_(2))
    assert_that(mock_get_actions_from_comms.call_count, is_(2))
    mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "default_action_code")
    mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "action_a")


@patch("eligibility_signposting_api.services.processors.action_rule_handler.RuleCalculator")
@patch.object(ActionRuleHandler, "get_actions_from_comms")
@patch.object(ActionRuleHandler, "get_action_rules_components")
def test_handle_multiple_rules_same_priority_one_mismatch(
    mock_get_action_rules_components,
    mock_get_actions_from_comms,
    mock_rule_calculator_class,
    action_rule_handler: ActionRuleHandler,
):
    rule1 = rule_builder.ICBRedirectRuleFactory.build(priority=10, comms_routing="action_a", name="RuleA")
    rule2 = rule_builder.ICBRedirectRuleFactory.build(priority=10, comms_routing="action_b", name="RuleB")
    active_iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_action_code",
        actions_mapper=ActionsMapperFactory.build(
            root={
                "default_action_code": DEFAULT_COMMS_DETAIL,
                "action_a": BOOK_NBS_COMMS,
                "action_b": DEFAULT_COMMS_DETAIL,
            }
        ),
        iteration_rules=[rule1, rule2],
    )
    rule_type = RuleType.redirect

    mock_get_action_rules_components.return_value = (
        (rule1, rule2),
        active_iteration.actions_mapper,
        active_iteration.default_comms_routing,
    )

    mock_get_actions_from_comms.side_effect = [
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType("DefaultInfoText"),
                action_code=ActionCode("DefaultHealthcareProInfo"),
                action_description=ActionDescription("Default Speak to your healthcare professional."),
                url_link=None,
                url_label=None,
            )
        ]
    ]

    mock_rule_calculator_class.side_effect = [
        Mock(evaluate_exclusion=Mock(return_value=(Status.actionable, Mock(matcher_matched=True)))),
        Mock(evaluate_exclusion=Mock(return_value=(Status.actionable, Mock(matcher_matched=False)))),
    ]

    matched_action_detail = action_rule_handler.handle(MOCK_PERSON, active_iteration, rule_type)

    assert_that(len(matched_action_detail.actions), is_(1))
    assert_that(matched_action_detail.actions[0].internal_action_code, is_(InternalActionCode("default_action_code")))
    assert_that(matched_action_detail.rule_priority, is_(None))
    assert_that(matched_action_detail.rule_name, is_(None))

    mock_get_action_rules_components.assert_called_once_with(active_iteration, rule_type)
    assert_that(mock_get_actions_from_comms.call_count, is_(1))
    mock_get_actions_from_comms.assert_called_once_with(active_iteration.actions_mapper, "default_action_code")
    assert_that(
        mock_rule_calculator_class.call_args_list,
        is_([call(person=MOCK_PERSON, rule=rule1), call(person=MOCK_PERSON, rule=rule2)]),
    )


@patch("eligibility_signposting_api.services.processors.action_rule_handler.RuleCalculator")
@patch.object(ActionRuleHandler, "get_actions_from_comms")
@patch.object(ActionRuleHandler, "get_action_rules_components")
def test_handle_different_priority_rules_highest_priority_wins(
    mock_get_action_rules_components,
    mock_get_actions_from_comms,
    mock_rule_calculator_class,
    action_rule_handler: ActionRuleHandler,
):
    lower_priority_rule = rule_builder.ICBRedirectRuleFactory.build(
        priority=20, comms_routing="action_low", name="LowP"
    )
    higher_priority_rule = rule_builder.ICBRedirectRuleFactory.build(
        priority=10, comms_routing="action_high", name="HighP"
    )
    active_iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_action_code",
        actions_mapper=ActionsMapperFactory.build(
            root={
                "default_action_code": DEFAULT_COMMS_DETAIL,
                "action_low": DEFAULT_COMMS_DETAIL,
                "action_high": BOOK_NBS_COMMS,
            }
        ),
        iteration_rules=[lower_priority_rule, higher_priority_rule],
    )
    rule_type = RuleType.redirect

    mock_get_action_rules_components.return_value = (
        (lower_priority_rule, higher_priority_rule),
        active_iteration.actions_mapper,
        active_iteration.default_comms_routing,
    )

    mock_get_actions_from_comms.side_effect = [
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType("DefaultInfoText"),
                action_code=ActionCode("DefaultHealthcareProInfo"),
                action_description=ActionDescription("Default Speak to your healthcare professional."),
                url_link=None,
                url_label=None,
            )
        ],
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("action_high"),
                action_type=ActionType("ButtonAuthLink"),
                action_code=ActionCode("BookNBS"),
                action_description=ActionDescription("Action description"),
                url_link=UrlLink(HttpUrl("https://www.nhs.uk/book-rsv")),
                url_label=UrlLabel("Continue to booking"),
            )
        ],
        [
            SuggestedAction(
                internal_action_code=InternalActionCode("action_low"),
                action_type=ActionType("CareCardWithText"),
                action_code=ActionCode("BookLocal"),
                action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
                url_link=None,
                url_label=None,
            )
        ],
    ]

    mock_rule_calculator_class.side_effect = [
        Mock(evaluate_exclusion=Mock(return_value=(Status.actionable, Mock(matcher_matched=True)))),
        Mock(evaluate_exclusion=Mock(return_value=(Status.actionable, Mock(matcher_matched=True)))),
    ]

    matched_action_detail = action_rule_handler.handle(MOCK_PERSON, active_iteration, rule_type)

    assert_that(len(matched_action_detail.actions), is_(1))
    assert_that(matched_action_detail.actions[0].internal_action_code, is_(InternalActionCode("action_high")))
    assert_that(matched_action_detail.rule_priority, is_(RulePriority(10)))
    assert_that(matched_action_detail.rule_name, is_(RuleName("HighP")))

    assert_that(mock_rule_calculator_class.call_count, is_(1))
    mock_rule_calculator_class.assert_called_once_with(person=MOCK_PERSON, rule=higher_priority_rule)
    assert_that(mock_get_actions_from_comms.call_count, is_(2))
    mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "default_action_code")
    mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "action_high")


def test_handle_no_actions_mapper_entry_for_rule_comms_returns_default(action_rule_handler: ActionRuleHandler):
    matching_rule = rule_builder.ICBRedirectRuleFactory.build(
        priority=10, comms_routing="non_existent_action", name="RuleSpecificAction"
    )
    active_iteration = rule_builder.IterationFactory.build(
        default_comms_routing="default_action_code",
        actions_mapper=ActionsMapperFactory.build(root={"default_action_code": DEFAULT_COMMS_DETAIL}),
        iteration_rules=[matching_rule],
    )
    rule_type = RuleType.redirect

    with (
        patch.object(ActionRuleHandler, "get_action_rules_components") as mock_get_action_rules_components,
        patch.object(ActionRuleHandler, "get_actions_from_comms") as mock_get_actions_from_comms,
        patch(
            "eligibility_signposting_api.services.processors.action_rule_handler.RuleCalculator"
        ) as mock_rule_calculator_class,
    ):
        mock_get_action_rules_components.return_value = (
            (matching_rule,),
            active_iteration.actions_mapper,
            active_iteration.default_comms_routing,
        )
        mock_get_actions_from_comms.side_effect = [
            [
                SuggestedAction(
                    internal_action_code=InternalActionCode("default_action_code"),
                    action_type=ActionType("DefaultInfoText"),
                    action_code=ActionCode("DefaultHealthcareProInfo"),
                    action_description=ActionDescription("Default Speak to your healthcare professional."),
                    url_link=None,
                    url_label=None,
                )
            ],
            None,
        ]
        mock_rule_calculator_class.return_value.evaluate_exclusion.return_value = (
            Status.actionable,
            Mock(matcher_matched=True),
        )

        matched_action_detail = action_rule_handler.handle(MOCK_PERSON, active_iteration, rule_type)

        assert_that(len(matched_action_detail.actions), is_(1))
        assert_that(
            matched_action_detail.actions[0].internal_action_code, is_(InternalActionCode("default_action_code"))
        )
        assert_that(matched_action_detail.rule_priority, is_(RulePriority(10)))
        assert_that(matched_action_detail.rule_name, is_(RuleName("RuleSpecificAction")))

        assert_that(mock_get_actions_from_comms.call_count, is_(2))
        mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "default_action_code")
        mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "non_existent_action")
        mock_rule_calculator_class.assert_called_once()


def test_handle_no_default_comms_and_no_matching_rule(action_rule_handler: ActionRuleHandler):
    active_iteration = rule_builder.IterationFactory.build(
        default_comms_routing="",
        actions_mapper=ActionsMapperFactory.build(root={}),
        iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(comms_routing="some_action")],
    )
    rule_type = RuleType.redirect

    with (
        patch.object(ActionRuleHandler, "get_action_rules_components") as mock_get_action_rules_components,
        patch.object(ActionRuleHandler, "get_actions_from_comms") as mock_get_actions_from_comms,
        patch(
            "eligibility_signposting_api.services.processors.action_rule_handler.RuleCalculator"
        ) as mock_rule_calculator_class,
    ):
        mock_get_action_rules_components.return_value = (
            (rule_builder.ICBRedirectRuleFactory.build(comms_routing="some_action"),),
            active_iteration.actions_mapper,
            None,
        )
        mock_get_actions_from_comms.side_effect = [None, None]
        mock_rule_calculator_class.return_value.evaluate_exclusion.return_value = (
            Status.actionable,
            Mock(matcher_matched=True),
        )

        matched_action_detail = action_rule_handler.handle(MOCK_PERSON, active_iteration, rule_type)

        assert_that(matched_action_detail.actions, is_(None))
        assert_that(matched_action_detail.rule_priority, is_(RulePriority(20)))
        assert_that(matched_action_detail.rule_name, is_(RuleName("In QE1")))

        assert_that(mock_get_actions_from_comms.call_count, is_(2))
        mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, None)
        mock_get_actions_from_comms.assert_any_call(active_iteration.actions_mapper, "some_action")
        mock_rule_calculator_class.assert_called_once()
