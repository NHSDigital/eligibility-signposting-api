import uuid
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from flask import Flask, g, request
from pydantic import HttpUrl

from eligibility_signposting_api.audit.audit_context import AuditContext
from eligibility_signposting_api.audit.audit_models import AuditAction, AuditEvent
from eligibility_signposting_api.audit.audit_service import AuditService
from eligibility_signposting_api.model.eligibility import (
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
    Status,
    SuggestedAction,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.model.rules import CampaignID, CampaignVersion, Iteration, RuleType
from tests.fixtures.builders.model.rule import IterationFactory


@pytest.fixture
def app():
    return Flask(__name__)


def test_add_request_details_sets_audit_log_on_g(app):
    headers = {
        "X-Request-ID": "test-x-request-id",
        "X-Correlation-ID": "test-x-correlation-id",
        "NHSD-End-User-Organisation-ODS": "test-org",
        "nhsd-application-id": "test-app-id",
    }

    nhs_number = "1234567890"
    url = "/patient-check?includeActions=Y"

    with app.test_request_context(url, headers=headers, method="GET"):
        request.view_args = {"nhs_number": nhs_number}
        AuditContext.add_request_details(request)

        assert hasattr(g, "audit_log")
        audit_req = g.audit_log.request
        assert audit_req.nhs_number == nhs_number
        assert audit_req.headers.x_request_id == "test-x-request-id"
        assert audit_req.headers.x_correlation_id == "test-x-correlation-id"
        assert audit_req.headers.nhsd_end_user_organisation_ods == "test-org"
        assert audit_req.headers.nhsd_application_id == "test-app-id"
        assert audit_req.query_params.include_actions == "Y"
        assert isinstance(audit_req.request_timestamp, datetime)


def test_add_request_details_when_headers_are_empty_sets_audit_log_on_g(app):
    nhs_number = "1234567890"
    url = "/patient-check?includeActions=Y"

    with app.test_request_context(url, method="GET"):
        request.view_args = {"nhs_number": nhs_number}
        AuditContext.add_request_details(request)

        assert hasattr(g, "audit_log")
        audit_req = g.audit_log.request
        assert audit_req.nhs_number == nhs_number
        assert audit_req.headers.x_request_id is None
        assert audit_req.headers.x_correlation_id is None
        assert audit_req.headers.nhsd_end_user_organisation_ods is None
        assert audit_req.headers.nhsd_application_id is None
        assert audit_req.query_params.include_actions == "Y"
        assert isinstance(audit_req.request_timestamp, datetime)


def test_append_audit_condition_adds_condition_to_audit_log_on_g(app):
    suggested_actions: list[SuggestedAction] | None
    condition_name: ConditionName
    best_results: tuple[Iteration, IterationResult, dict[str, CohortGroupResult]]
    campaign_details: tuple[CampaignID | None, CampaignVersion | None]
    redirect_rule_details: tuple[RulePriority | None, RuleName | None]

    suggested_actions = [
        SuggestedAction(
            internal_action_code=InternalActionCode("InternalActionCode1"),
            action_code=ActionCode("ActionCode1"),
            action_type=ActionType("ActionType1"),
            action_description=ActionDescription("ActionDescription1"),
            url_link=UrlLink(HttpUrl("https://example.com/")),
            url_label=UrlLabel("ActionLabel1"),
        )
    ]

    condition_name = ConditionName("Condition1")
    iteration = IterationFactory.build()
    audit_rules = [
        Reason(
            rule_type=RuleType.filter,
            rule_name=RuleName("FilterRuleName1"),
            rule_description=RuleDescription("FilterRuleDescription1"),
            matcher_matched=True,
            rule_priority=RulePriority("1"),
        )
    ]
    cohort_group_result = CohortGroupResult(
        status=Status.actionable,
        cohort_code="CohortCode1",
        description="CohortDescription1",
        audit_rules=audit_rules,
        reasons=audit_rules,
    )
    iteration_result = IterationResult(
        status=Status.actionable, cohort_results=[cohort_group_result], actions=suggested_actions
    )
    best_results = (iteration, iteration_result, {"CohortCode1": cohort_group_result})
    campaign_details = (CampaignID("CampaignID1"), CampaignVersion("CampaignVersion1"))
    redirect_rule_details = (RulePriority("1"), RuleName("RedirectRuleName1"))

    with app.app_context():
        g.audit_log = AuditEvent()

        AuditContext.append_audit_condition(
            suggested_actions, condition_name, best_results, campaign_details, redirect_rule_details
        )

        expected_audit_action = [
            AuditAction(
                internal_action_code="InternalActionCode1",
                action_code="ActionCode1",
                action_type="ActionType1",
                action_description="ActionDescription1",
                action_url="https://example.com/",
                action_url_label="ActionLabel1",
            )
        ]

        assert g.audit_log.response.condition, condition_name
        cond = g.audit_log.response.condition[0]
        assert cond.condition_name == condition_name
        assert cond.campaign_id == campaign_details[0]
        assert cond.campaign_version == campaign_details[1]
        assert cond.iteration_id == iteration.id
        assert cond.iteration_version == iteration.version
        assert cond.status == best_results[1].status.name
        assert cond.status_text == "You should have the Condition1 vaccine"
        assert cond.actions == expected_audit_action
        assert cond.action_rule.rule_priority == "1"
        assert cond.action_rule.rule_name == "RedirectRuleName1"
        assert cond.suitability_rules is None
        assert cond.filter_rules is None
        assert cond.eligibility_cohorts[0].cohort_code == "CohortCode1"
        assert cond.eligibility_cohorts[0].cohort_status == "actionable"
        assert cond.eligibility_cohort_groups[0].cohort_code == "CohortCode1"
        assert cond.eligibility_cohort_groups[0].cohort_status == "actionable"
        assert cond.eligibility_cohort_groups[0].cohort_text == "CohortDescription1"


def test_add_response_details_adds_to_audit_log_on_g(app):
    response_id = uuid.uuid4()
    last_updated = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

    with app.app_context():
        g.audit_log = AuditEvent()

        AuditContext.add_response_details(response_id, last_updated)

        assert g.audit_log.response.response_id == response_id
        assert g.audit_log.response.last_updated is last_updated


def test_write_to_firehose_calls_audit_service_with_correct_data_from_g(app):
    mock_audit_service = Mock(spec=AuditService)
    response_id = uuid.uuid4()
    last_updated = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

    with app.app_context():
        g.audit_log = AuditEvent()

        AuditContext.add_response_details(response_id, last_updated)
        AuditContext.write_to_firehose(mock_audit_service)

        assert g.audit_log.response.response_id == response_id
        assert g.audit_log.response.last_updated == last_updated

        mock_audit_service.audit.assert_called_once_with(g.audit_log.model_dump(by_alias=True))
