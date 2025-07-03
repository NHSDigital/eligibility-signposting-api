import logging
from dataclasses import asdict
from datetime import UTC, datetime
from operator import attrgetter

from flask import Request, g

from eligibility_signposting_api.audit_models import (
    AuditAction,
    AuditCondition,
    AuditEligibilityCohortGroups,
    AuditEligibilityCohorts,
    AuditFilterRule,
    AuditRedirectRule,
    AuditSuitabilityRule,
    RequestAuditData,
    RequestAuditHeader,
    RequestAuditQueryParams,
)
from eligibility_signposting_api.model.eligibility import (
    CohortGroupResult,
    ConditionName,
    IterationResult,
    Status,
    SuggestedActions,
)
from eligibility_signposting_api.model.rules import CampaignID, CampaignVersion, Iteration, RuleName, RulePriority
from eligibility_signposting_api.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AuditContext:
    @staticmethod
    def add_request_details(request: Request) -> None:
        resource_id = None

        if "nhs_number" in request.view_args:
            try:
                resource_id = int(request.view_args["nhs_number"])
            except (ValueError, TypeError):
                logger.exception("Could not parse 'nhs_number' from path parameters")  # TODO: fix log
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
        suggested_actions: SuggestedActions | None,
        condition_name: ConditionName,
        best_results: tuple[Iteration, IterationResult, dict[str, CohortGroupResult]],
        campaign_details: tuple[CampaignID | None, CampaignVersion | None],
        redirect_rule_details: tuple[RulePriority | None, RuleName | None],
    ) -> None:
        audit_eligibility_cohorts, audit_eligibility_cohort_groups, audit_actions = [], [], []
        audit_filter_rule, audit_suitability_rule, audit_redirect_rule = None, None, None
        best_active_iteration = best_results[0]
        best_candidate = best_results[1]
        best_cohort_results = best_results[2]

        for value in sorted(best_cohort_results.values(), key=attrgetter("cohort_code")):
            audit_eligibility_cohorts.append(
                AuditEligibilityCohorts(cohort_code=value.cohort_code, cohort_status=value.status.name)
            )

            audit_eligibility_cohort_groups.append(
                AuditEligibilityCohortGroups(
                    cohort_code=value.cohort_code, cohort_status=value.status.name, cohort_text=value.description
                )
            )

            # TODO: what if value.audit_reasons is empty?
            if value.audit_reasons:
                if best_candidate.status.name == Status.not_eligible.name:
                    audit_filter_rule = AuditFilterRule(
                        rule_priority=value.audit_reasons[0].rule_priority, rule_name=value.audit_reasons[0].rule_name
                    )
                if best_candidate.status.name == Status.not_actionable.name:
                    audit_suitability_rule = AuditSuitabilityRule(
                        rule_priority=value.audit_reasons[0].rule_priority,
                        rule_name=value.audit_reasons[0].rule_name,
                        rule_message=value.audit_reasons[0].rule_description,
                    )

        if best_candidate.status.name == Status.actionable.name:
            audit_redirect_rule = AuditRedirectRule(redirect_rule_details[0], redirect_rule_details[1])

        if suggested_actions is None or suggested_actions == []:
            audit_actions = suggested_actions

        elif len(suggested_actions.actions) > 0:
            for action in suggested_actions.actions:
                audit_actions.append(
                    AuditAction(action_code=action.action_code, action_description=action.action_description)
                )

        audit_condition = AuditCondition(
            campaign_id=campaign_details[0],
            campaign_version=campaign_details[1],
            iteration_id=best_active_iteration.id,
            iteration_version=best_active_iteration.version,
            condition_name=condition_name,
            status=best_candidate.status.name,
            status_text=best_candidate.status.name,
            eligibility_cohorts=audit_eligibility_cohorts,
            eligibility_cohort_groups=audit_eligibility_cohort_groups,
            filter_rules=audit_filter_rule,
            suitability_rules=audit_suitability_rule,
            action_rule=audit_redirect_rule,
            actions=audit_actions,
        )

        g.audit_log.response.condition.append(audit_condition)  # TODO: check with multiple conditions

    @staticmethod
    def add_response_details(response) -> None:
        g.audit_log.response.response_id = str(response.response_id)
        g.audit_log.response.last_updated = str(response.meta.last_updated)

    @staticmethod
    def write_to_firehose(service: AuditService, response) -> None:
        AuditContext.add_response_details(response)
        service.audit(asdict(g.audit_log))
