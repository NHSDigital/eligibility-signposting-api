from itertools import groupby
from operator import attrgetter

from eligibility_signposting_api.model.campaign_config import (
    ActionsMapper,
    Iteration,
    IterationRule,
)
from eligibility_signposting_api.model.eligibility_status import (
    ActionCode,
    ActionDescription,
    ActionType,
    InternalActionCode,
    IterationResult,
    MatchedActionDetail,
    RuleType,
    SuggestedAction,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator


class ActionRuleHandler:
    def get_actions(
        self,
        person: Person,
        active_iteration: Iteration | None,
        best_iteration_result: IterationResult,
        *,
        include_actions_flag: bool,
    ) -> MatchedActionDetail:
        action_detail = MatchedActionDetail()

        if active_iteration is not None and include_actions_flag:
            rule_type = best_iteration_result.status.get_action_rule_type()
            action_detail = self._handle(person, active_iteration, rule_type)

        return action_detail

    def _handle(self, person: Person, best_active_iteration: Iteration, rule_type: RuleType) -> MatchedActionDetail:
        action_rules, action_mapper, default_comms = self._get_action_rules_components(best_active_iteration, rule_type)

        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(action_rules, key=priority_getter)

        actions: list[SuggestedAction] | None = self._get_actions_from_comms(action_mapper, default_comms)  # pyright: ignore[reportArgumentType]

        matched_action_rule_priority, matched_action_rule_name = None, None
        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            rule_group_list = list(rule_group)
            matcher_matched_list = [
                RuleCalculator(person=person, rule=rule).evaluate_exclusion()[1].matcher_matched
                for rule in rule_group_list
            ]

            comms_routing = rule_group_list[0].comms_routing
            if comms_routing and all(matcher_matched_list):
                rule_actions = self._get_actions_from_comms(action_mapper, comms_routing)
                if rule_actions and len(rule_actions) > 0:
                    actions = rule_actions
                matched_action_rule_priority = rule_group_list[0].priority
                matched_action_rule_name = rule_group_list[0].name
                break

        return MatchedActionDetail(matched_action_rule_name, matched_action_rule_priority, actions)

    @staticmethod
    def _get_action_rules_components(
        active_iteration: Iteration, rule_type: RuleType
    ) -> tuple[tuple[IterationRule, ...], ActionsMapper, str | None]:
        action_rules = tuple(rule for rule in active_iteration.iteration_rules if rule.type in rule_type)

        routing_map = {
            RuleType.redirect: active_iteration.default_comms_routing,
            RuleType.not_eligible_actions: active_iteration.default_not_eligible_routing,
            RuleType.not_actionable_actions: active_iteration.default_not_actionable_routing,
        }

        default_comms = routing_map.get(rule_type)
        action_mapper = active_iteration.actions_mapper
        return action_rules, action_mapper, default_comms

    @staticmethod
    def _get_actions_from_comms(action_mapper: ActionsMapper, comms: str) -> list[SuggestedAction] | None:
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
