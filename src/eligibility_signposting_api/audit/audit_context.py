import logging
from datetime import UTC, datetime
from uuid import UUID

from flask import Request, g

from eligibility_signposting_api.audit.audit_models import (
    AuditAction,
    AuditCondition,
    AuditEligibilityCohortGroups,
    AuditEligibilityCohorts,
    AuditEvent,
    AuditFilterRule,
    AuditRedirectRule,
    AuditSuitabilityRule,
    RequestAuditData,
    RequestAuditHeader,
    RequestAuditQueryParams,
)
from eligibility_signposting_api.audit.audit_service import AuditService
from eligibility_signposting_api.model.eligibility_status import (
    BestIterationResult,
    CohortGroupResult,
    ConditionName,
    IterationResult,
    MatchedActionDetail,
    Status,
    SuggestedAction,
)

logger = logging.getLogger(__name__)


class AuditContext:
    @staticmethod
    def add_request_details(request: Request) -> None:
        g.audit_log = AuditEvent()
        resource_id = None
        if request.view_args and request.view_args["nhs_number"]:
            resource_id = request.view_args["nhs_number"]
        g.audit_log.request = RequestAuditData(
            nhs_number=resource_id,
            request_timestamp=datetime.now(tz=UTC),
            headers=(
                RequestAuditHeader(
                    x_request_id=request.headers.get("X-Request-ID"),
                    x_correlation_id=request.headers.get("X-Correlation-ID"),
                    nhsd_end_user_organisation_ods=request.headers.get("NHSD-End-User-Organisation-ODS"),
                    nhsd_application_id=request.headers.get("nhsd-application-id"),
                )
            ),
            query_params=(
                RequestAuditQueryParams(
                    category=request.args.get("category"),
                    conditions=request.args.get("conditions"),
                    include_actions=request.args.get("includeActions"),
                )
            ),
        )

    @staticmethod
    def append_audit_condition(
        condition_name: ConditionName,
        best_iteration_result: BestIterationResult,
        action_detail: MatchedActionDetail,
    ) -> None:
        audit_eligibility_cohorts, audit_eligibility_cohort_groups, audit_actions = [], [], []
        audit_filter_rule, audit_suitability_rule, audit_action_rule = None, None, None
        best_active_iteration = best_iteration_result.active_iteration
        best_candidate = best_iteration_result.iteration_result
        best_cohort_results = best_iteration_result.cohort_results

        if best_cohort_results:
            for cohort_label, result in sorted(best_cohort_results.items(), key=lambda item: item[1].cohort_code):
                cohort_status_name = result.status.name if result.status else None
                audit_eligibility_cohorts.append(
                    AuditEligibilityCohorts(cohort_code=cohort_label, cohort_status=cohort_status_name)
                )

                audit_eligibility_cohort_groups.append(
                    AuditEligibilityCohortGroups(
                        cohort_code=result.cohort_code, cohort_status=cohort_status_name, cohort_text=result.description
                    )
                )

                if result.audit_rules and best_candidate:
                    audit_filter_rule = AuditContext.create_audit_filter_rule(best_candidate, result)
                    audit_suitability_rule = AuditContext.create_audit_suitability_rule(best_candidate, result)

        audit_action_rule = AuditContext.add_rule_name_and_priority_to_audit(best_candidate, action_detail)

        audit_actions = AuditContext.create_audit_actions(action_detail.actions)

        audit_condition = AuditCondition(
            campaign_id=best_iteration_result.campaign_id,
            campaign_version=best_iteration_result.campaign_version,
            iteration_id=best_active_iteration.id if best_active_iteration else None,
            iteration_version=best_active_iteration.version if best_active_iteration else None,
            condition_name=condition_name,
            status=best_candidate.status.name if best_candidate and best_candidate.status else None,
            status_text=best_candidate.status.get_status_text(condition_name) if best_candidate else None,
            eligibility_cohorts=audit_eligibility_cohorts,
            eligibility_cohort_groups=audit_eligibility_cohort_groups,
            filter_rules=audit_filter_rule,
            suitability_rules=audit_suitability_rule,
            action_rule=audit_action_rule,
            actions=audit_actions,
        )

        g.audit_log.response.condition.append(audit_condition)

    @staticmethod
    def add_rule_name_and_priority_to_audit(
        best_candidate: IterationResult | None,
        action_detail: MatchedActionDetail,
    ) -> AuditRedirectRule | None:
        audit_action_rule = None
        if best_candidate and best_candidate.status:
            if action_detail.rule_priority is None and action_detail.rule_name is None:
                audit_action_rule = None
            else:
                audit_action_rule = AuditRedirectRule(
                    rule_priority=str(action_detail.rule_priority), rule_name=action_detail.rule_name
                )
        return audit_action_rule

    @staticmethod
    def add_response_details(response_id: UUID, last_updated: datetime) -> None:
        g.audit_log.response.response_id = response_id
        g.audit_log.response.last_updated = last_updated

    @staticmethod
    def write_to_firehose(service: AuditService) -> None:
        service.audit(g.audit_log.model_dump(by_alias=True))

    @staticmethod
    def create_audit_actions(suggested_actions: list[SuggestedAction] | None) -> list[AuditAction] | None:
        audit_actions = []
        if suggested_actions is None:
            audit_actions = None
        elif len(suggested_actions) > 0:
            for action in suggested_actions:
                audit_actions.append(
                    AuditAction(
                        internal_action_code=action.internal_action_code,
                        action_code=action.action_code,
                        action_type=action.action_type,
                        action_description=action.action_description,
                        action_url=str(action.url_link) if action.url_link else None,
                        action_url_label=action.url_label,
                    )
                )
        return audit_actions

    @staticmethod
    def create_audit_suitability_rule(
        best_candidate: IterationResult, result: CohortGroupResult
    ) -> AuditSuitabilityRule | None:
        audit_suitability_rule = None
        if best_candidate.status and best_candidate.status.name == Status.not_actionable.name:
            audit_suitability_rule = AuditSuitabilityRule(
                rule_priority=result.audit_rules[0].rule_priority,
                rule_name=result.audit_rules[0].rule_name,
                rule_message=result.audit_rules[0].rule_description,
            )
        return audit_suitability_rule

    @staticmethod
    def create_audit_filter_rule(best_candidate: IterationResult, result: CohortGroupResult) -> AuditFilterRule | None:
        audit_filter_rule = None
        if best_candidate.status and best_candidate.status.name == Status.not_eligible.name:
            audit_filter_rule = AuditFilterRule(
                rule_priority=result.audit_rules[0].rule_priority,
                rule_name=result.audit_rules[0].rule_name,
            )
        return audit_filter_rule
