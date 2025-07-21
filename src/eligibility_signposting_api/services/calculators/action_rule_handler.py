from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter

from eligibility_signposting_api.model import rules
from eligibility_signposting_api.model.eligibility import (
    ActionCode,
    ActionDescription,
    ActionType,
    InternalActionCode,
    SuggestedAction,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.model.rules import ActionsMapper, Iteration, RuleName, RulePriority, RuleType
from eligibility_signposting_api.services.calculators.person_data_reader import PersonDataReader
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator


@dataclass
class ActionRuleHandler:
    person_data_reader: PersonDataReader

    def handle_action_rules(
        self, active_iteration: Iteration, rule_type: RuleType
    ) -> tuple[list[SuggestedAction] | None, RulePriority | None, RuleName | None]:
        action_rules, action_mapper, default_comms = self.get_action_rules_components(active_iteration, rule_type)
        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(action_rules, key=priority_getter)

        actions: list[SuggestedAction] | None = self.get_actions_from_comms(action_mapper, default_comms)

        matched_action_rule_priority, matched_action_rule_name = None, None
        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            rule_group_list = list(rule_group)
            matcher_matched_list = [
                RuleCalculator(person_data_reader=self.person_data_reader, rule=rule)
                .evaluate_exclusion()[1]
                .matcher_matched
                for rule in rule_group_list
            ]

            comms_routing = rule_group_list[0].comms_routing
            if comms_routing and all(matcher_matched_list):
                rule_actions = self.get_actions_from_comms(action_mapper, comms_routing)
                if rule_actions and len(rule_actions) > 0:
                    actions = rule_actions
                matched_action_rule_priority = rule_group_list[0].priority
                matched_action_rule_name = rule_group_list[0].name
                break

        return actions, matched_action_rule_priority, matched_action_rule_name

    @staticmethod
    def get_action_rules_components(
        active_iteration: Iteration, rule_type: RuleType
    ) -> tuple[tuple[rules.IterationRule, ...], ActionsMapper, str | None]:
        action_rules = tuple(rule for rule in active_iteration.iteration_rules if rule.type in rule_type)

        routing_map = {
            rules.RuleType.redirect: active_iteration.default_comms_routing,
            rules.RuleType.not_eligible_actions: active_iteration.default_not_eligible_routing,
            rules.RuleType.not_actionable_actions: active_iteration.default_not_actionable_routing,
        }

        default_comms = routing_map.get(rule_type)
        action_mapper = active_iteration.actions_mapper
        return action_rules, action_mapper, default_comms

    @staticmethod
    def get_actions_from_comms(action_mapper: ActionsMapper, comms: str) -> list[SuggestedAction] | None:
        suggested_actions: list[SuggestedAction] = []
        for comm in comms.split("|"):
            action = action_mapper.get(comm)
            if action is not None:
                suggested_actions.append(
                    SuggestedAction(
                        internal_action_code=InternalActionCode(comm),
                        action_type=ActionType(action.action_type),
                        action_code=ActionCode(action.action_code),
                        action_description=ActionDescription(action.action_description)
                        if action.action_description
                        else None,
                        url_link=UrlLink(action.url_link) if action.url_link else None,
                        url_label=UrlLabel(action.url_label) if action.url_label else None,
                    )
                )
        return suggested_actions
