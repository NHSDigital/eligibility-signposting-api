import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from flask import Flask, g, request

from eligibility_signposting_api.audit_context import AuditContext
from eligibility_signposting_api.audit_models import AuditEvent
from eligibility_signposting_api.model.eligibility import (
    ActionCode,
    ActionDescription,
    ActionType,
    CohortGroupResult,
    ConditionName,
    IterationResult,
    Reason,
    RuleDescription,
    RuleName,
    RulePriority,
    Status,
    SuggestedAction,
    SuggestedActions,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.model.rules import CampaignID, CampaignVersion, Iteration, RuleType
from eligibility_signposting_api.services.audit_service import AuditService
from tests.fixtures.builders.model.rule import IterationFactory
from tests.fixtures.builders.views.response_model.eligibility import EligibilityResponseFactory


@pytest.fixture
def app():
    app = Flask(__name__)
    return app


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
    suggested_actions: SuggestedActions | None
    condition_name: ConditionName
    best_results: tuple[Iteration, IterationResult, dict[str, CohortGroupResult]]
    campaign_details: tuple[CampaignID | None, CampaignVersion | None]
    redirect_rule_details: tuple[RulePriority | None, RuleName | None]

    suggested_actions = SuggestedActions(
        actions=[
            SuggestedAction(
                action_code=ActionCode("ActionCode1"),
                action_type=ActionType("ActionType1"),
                action_description=ActionDescription("ActionDescription1"),
                url_link=UrlLink("https://www.example.com"),
                url_label=UrlLabel("ActionLabel1"),
            )
        ]
    )

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

        assert g.audit_log.response.condition, condition_name
        cond = g.audit_log.response.condition[0]
        assert cond.condition_name == condition_name
        assert cond.campaign_id == campaign_details[0]
        assert cond.status == best_results[1].status.name
        assert cond.status_text == best_results[1].status.name


def test_add_response_details_adds_to_audit_log_on_G(app):
    eligibility_response = EligibilityResponseFactory.build(
        response_id=uuid.uuid4(), meta={"last_updated": datetime(2023, 1, 1, 0, 0)}, processed_suggestions=[]
    )

    with app.app_context():
        g.audit_log = AuditEvent()

        AuditContext.add_response_details(eligibility_response)

        assert g.audit_log.response.response_id == eligibility_response.response_id
        assert g.audit_log.response.last_updated is eligibility_response.meta.last_updated


def test_write_to_firehose_calls_audit_service_with_correct_data_from_g(app):
    mock_audit_service = Mock(spec=AuditService)
    eligibility_response = EligibilityResponseFactory.build(
        response_id=(uuid.uuid4()),
        meta={"last_updated": (datetime(2023, 1, 1, 0, 0, tzinfo=UTC))},
        processed_suggestions=[],
    )

    with app.app_context():
        g.audit_log = AuditEvent()

        AuditContext.write_to_firehose(mock_audit_service, eligibility_response)

        assert g.audit_log.response.response_id == eligibility_response.response_id
        assert g.audit_log.response.last_updated == eligibility_response.meta.last_updated

        mock_audit_service.audit.assert_called_once_with(asdict(g.audit_log))
