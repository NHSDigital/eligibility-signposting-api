import logging
from datetime import datetime
from itertools import groupby
from operator import attrgetter

from eligibility_signposting_api.model.eligibility import CohortGroupResult, Status
from eligibility_signposting_api.audit_models import RequestAuditData, RequestAuditHeader, RequestAuditQueryParams, \
    AuditEligibilityCohorts, AuditEligibilityCohortGroups, AuditAction, AuditCondition, AuditRedirectRule, \
    AuditFilterRule, AuditSuitabilityRule

logger = logging.getLogger(__name__)

from flask import Request, g, Response


class AuditService:

    @staticmethod
    def add_request_details(request: Request) -> None:
        resource_id = None
        if 'id' in request.view_args:
            try:
                resource_id = int(request.view_args['id'])
            except (ValueError, TypeError):
                logger.warning(f"Could not parse 'id' from path parameters: {request.view_args.get('id')}")
        g.audit_log.request = RequestAuditData(
            nhsNumber=resource_id,
            requestTimestamp=datetime.now(),
            headers=(RequestAuditHeader(
                xRequestID=request.headers.get("X-Request-ID"),
                xCorrelationID=request.headers.get("X-Correlation-ID"),
                nhsdEndUserOrganisationODS=request.headers.get("NHSD-End-User-Organisation-ODS"),
                nhsdApplicationID=request.headers.get("nhsd-application-id")
            )),
            queryParams=(RequestAuditQueryParams(
                category=request.args.get("category"),
                conditions=request.args.get("conditions"),
                includeActions=request.args.get("include_actions")
            )),
        )


    @staticmethod
    def add_response_details(response: Response) -> None:
        pass

    @staticmethod
    def append_audit_condition(suggested_actions, best_active_iteration, best_candidate, campaign_id, campaign_version,
                               condition_name, best_cohort_results: dict[str, CohortGroupResult], priority, name):

        audit_eligibility_cohorts, audit_eligibility_cohort_groups, audit_actions = [], [], []
        audit_filter_rule, audit_suitability_rule, audit_redirect_rule = None, None, None

        for value in sorted(best_cohort_results.values(), key=attrgetter("cohort_code")):
            audit_eligibility_cohorts.append(
                AuditEligibilityCohorts(cohortCode=value.cohort_code, cohortStatus=value.status.name))

            audit_eligibility_cohort_groups.append(
                AuditEligibilityCohortGroups(cohortCode=value.cohort_code, cohortStatus=value.status.name,
                                             cohortText=value.description))

            # TODO: what if value.audit_reasons is empty?
            if value.audit_reasons:
                if best_candidate.status.name == Status.not_eligible.name:
                    audit_filter_rule = AuditFilterRule(rulePriority=value.audit_reasons[0].rule_priority,
                                                        ruleName=value.audit_reasons[0].rule_name)
                if best_candidate.status.name == Status.not_actionable.name:
                    audit_suitability_rule = AuditSuitabilityRule(rulePriority=value.audit_reasons[0].rule_priority,
                                                                  ruleName=value.audit_reasons[0].rule_name,
                                                                  ruleMessage=value.audit_reasons[0].rule_description)

        if best_candidate.status.name == Status.actionable.name:
            audit_redirect_rule = AuditRedirectRule(priority, name)

        if suggested_actions is None or suggested_actions == []:
            audit_actions = suggested_actions

        elif len(suggested_actions.actions) > 0:
            for action in suggested_actions.actions:
                audit_actions.append(
                    AuditAction(actionCode=action.action_code, actionDescription=action.action_description))

        audit_condition = AuditCondition(campaignID=campaign_id,
                                         campaignVersion=campaign_version,  # TODO: Convert to int
                                         iterationID=best_active_iteration.id,
                                         iterationVersion=best_active_iteration.version,  # TODO: Convert to int
                                         conditionName=condition_name,
                                         status=best_candidate.status.name,
                                         statusText=best_candidate.status.name,  # Same as status per source code
                                         eligibilityCohorts=audit_eligibility_cohorts,
                                         eligibilityCohortGroups=audit_eligibility_cohort_groups,
                                         filterRules=audit_filter_rule,
                                         suitabilityRules=audit_suitability_rule,
                                         actionRule=audit_redirect_rule,
                                         actions=audit_actions)

        print(">>> audit_condition:", audit_condition)

        # g.audit_log.response.condition.append(audit_condition)
