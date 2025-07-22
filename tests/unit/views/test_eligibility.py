import json
import logging
from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask import Flask
from flask.testing import FlaskClient
from hamcrest import assert_that, contains_exactly, has_entries, has_length, is_, none
from wireup.integration.flask import get_app_container

from eligibility_signposting_api.audit.audit_service import AuditService
from eligibility_signposting_api.model.eligibility_status import (
    ActionCode,
    ActionDescription,
    ActionType,
    CohortGroupResult,
    Condition,
    EligibilityStatus,
    NHSNumber,
    Reason,
    RuleDescription,
    RuleName,
    RulePriority,
    RuleType,
    Status,
    SuggestedAction,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.views.eligibility import (
    build_actions,
    build_eligibility_cohorts,
    build_suitability_results,
    get_or_default_query_params,
)
from eligibility_signposting_api.views.response_model import eligibility_response
from tests.fixtures.builders.model.eligibility import (
    CohortResultFactory,
    ConditionFactory,
    EligibilityStatusFactory,
)
from tests.fixtures.matchers.eligibility import is_eligibility_cohort, is_suitability_rule

logger = logging.getLogger(__name__)


class FakeAuditService:
    def audit(self, audit_record):
        pass


class FakeEligibilityService(EligibilityService):
    def __init__(self):
        pass

    def get_eligibility_status(
        self,
        _nhs_number: NHSNumber,
        _include_actions: str,
        _conditions: list[str],
        _category: str,
    ) -> EligibilityStatus:
        return EligibilityStatusFactory.build()


class FakeUnknownPersonEligibilityService(EligibilityService):
    def __init__(self):
        pass

    def get_eligibility_status(
        self,
        _nhs_number: NHSNumber,
        _include_actions: str,
        _conditions: list[str],
        _category: str,
    ) -> EligibilityStatus:
        raise UnknownPersonError


class FakeUnexpectedErrorEligibilityService(EligibilityService):
    def __init__(self):
        pass

    def get_eligibility_status(
        self,
        _nhs_number: NHSNumber,
        _include_actions: str,
        _conditions: list[str],
        _category: str,
    ) -> EligibilityStatus:
        raise ValueError


def test_nhs_number_given(app: Flask, client: FlaskClient):
    # Given
    with (
        get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()),
        get_app_container(app).override.service(AuditService, new=FakeAuditService()),
    ):
        # When
        response = client.get("/patient-check/12345")

        # Then
        assert_that(response, is_response().with_status_code(HTTPStatus.OK))


def test_no_nhs_number_given(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeUnknownPersonEligibilityService()):
        # When
        response = client.get("/patient-check/")

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.NOT_FOUND)
        .with_headers(has_entries({"Content-Type": "application/fhir+json"}))
        .and_text(
            is_json_that(
                has_entries(
                    resourceType="OperationOutcome",
                    issue=contains_exactly(
                        has_entries(
                            severity="error",
                            code="processing",
                            diagnostics="NHS Number '' was not recognised by the Eligibility Signposting API",
                            details={
                                "coding": [
                                    {
                                        "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                        "code": "REFERENCE_NOT_FOUND",
                                        "display": "The given NHS number was not found in our datasets. "
                                        "This could be because the number is incorrect or "
                                        "some other reason we cannot process that number.",
                                    }
                                ]
                            },
                        )
                    ),
                )
            )
        ),
    )


def test_unexpected_error(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeUnexpectedErrorEligibilityService()):
        response = client.get("/patient-check/12345")

        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.INTERNAL_SERVER_ERROR)
            .with_headers(has_entries({"Content-Type": "application/fhir+json"}))
            .and_text(
                is_json_that(
                    has_entries(
                        resourceType="OperationOutcome",
                        issue=contains_exactly(
                            has_entries(
                                severity="error",
                                code="processing",
                                diagnostics="An unexpected error occurred.",
                                details={
                                    "coding": [
                                        {
                                            "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                            "code": "INTERNAL_SERVER_ERROR",
                                            "display": "An unexpected internal server error occurred.",
                                        }
                                    ]
                                },
                            )
                        ),
                    )
                )
            ),
        )


@pytest.mark.parametrize(
    ("cohort_results", "expected_eligibility_cohorts", "test_comment"),
    [
        (
            [
                CohortResultFactory.build(
                    cohort_code="CohortCode1", status=Status.not_actionable, description="+ve des 1"
                ),
                CohortResultFactory.build(
                    cohort_code="CohortCode2", status=Status.not_actionable, description="+ve des 2"
                ),
            ],
            [
                ("CohortCode1", "NotActionable", "+ve des 1"),
                ("CohortCode2", "NotActionable", "+ve des 2"),
            ],
            "two cohort group codes with same status, nothing is ignored",
        ),
        (
            [
                CohortResultFactory.build(
                    cohort_code="CohortCode1", status=Status.not_actionable, description="+ve des 1"
                ),
                CohortResultFactory.build(cohort_code="CohortCode2", status=Status.not_actionable, description=None),
                CohortResultFactory.build(cohort_code="CohortCode3", status=Status.not_actionable, description=""),
            ],
            [("CohortCode1", "NotActionable", "+ve des 1")],
            "only one cohort has description",
        ),
        (
            [
                CohortResultFactory.build(cohort_code="some_cohort", status=Status.not_actionable, description=""),
            ],
            [],
            "only one cohort but no description, so it is ignored",
        ),
        (
            [
                CohortResultFactory.build(cohort_code="some_cohort", status=Status.not_actionable, description=None),
            ],
            [],
            "only one cohort but no description, so it is ignored",
        ),
    ],
)
def test_build_eligibility_cohorts_results_consider_only_cohorts_groups_that_has_description(
    cohort_results: list[CohortGroupResult], expected_eligibility_cohorts: list[tuple[str, str, str]], test_comment
):
    condition: Condition = ConditionFactory.build(
        status=Status.not_actionable,
        cohort_results=cohort_results,
    )

    results = build_eligibility_cohorts(condition)

    assert_that(
        results,
        contains_exactly(
            *[
                is_eligibility_cohort().with_cohort_code(item[0]).and_cohort_status(item[1]).and_cohort_text(item[2])
                for item in expected_eligibility_cohorts
            ]
        ),
        test_comment,
    )


def test_build_suitability_results_with_deduplication():
    condition: Condition = ConditionFactory.build(
        status=Status.not_actionable,
        cohort_results=[
            CohortResultFactory.build(
                cohort_code="cohort_group1",
                status=Status.not_actionable,
                reasons=[
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude too young less than 75"),
                        rule_description=RuleDescription("your age is greater than 75"),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude too young less than 75"),
                        rule_description=RuleDescription("your age is greater than 75"),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude more than 100"),
                        rule_description=RuleDescription("your age is greater than 100"),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    ),
                ],
            ),
            CohortResultFactory.build(
                cohort_code="cohort_group2",
                status=Status.not_actionable,
                reasons=[
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude too young less than 75"),
                        rule_description=RuleDescription("your age is greater than 75"),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    )
                ],
            ),
            CohortResultFactory.build(
                cohort_code="cohort_group3",
                status=Status.not_eligible,
                reasons=[
                    Reason(
                        rule_type=RuleType.filter,
                        rule_name=RuleName("Exclude is present in sw1"),
                        rule_description=RuleDescription("your a member of sw1"),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    )
                ],
            ),
            CohortResultFactory.build(
                cohort_code="cohort_group4",
                description="",
                status=Status.not_actionable,
                reasons=[
                    Reason(
                        rule_type=RuleType.filter,
                        rule_name=RuleName("Already vaccinated"),
                        rule_description=RuleDescription("you have already vaccinated"),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    )
                ],
            ),
        ],
    )

    results = build_suitability_results(condition)

    assert_that(
        results,
        contains_exactly(
            is_suitability_rule()
            .with_rule_code("Exclude too young less than 75")
            .and_rule_text("your age is greater than 75"),
            is_suitability_rule().with_rule_code("Exclude more than 100").and_rule_text("your age is greater than 100"),
            is_suitability_rule().with_rule_code("Already vaccinated").and_rule_text("you have already vaccinated"),
        ),
    )


def test_build_suitability_results_when_rule_text_is_empty_or_null():
    condition: Condition = ConditionFactory.build(
        status=Status.not_actionable,
        cohort_results=[
            CohortResultFactory.build(
                cohort_code="cohort_group1",
                status=Status.not_actionable,
                reasons=[
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude too young less than 75"),
                        rule_description=RuleDescription("your age is greater than 75"),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude more than 100"),
                        rule_description=RuleDescription(""),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude more than 100"),
                        matcher_matched=False,
                        rule_description=None,
                        rule_priority=RulePriority(1),
                    ),
                ],
            ),
            CohortResultFactory.build(
                cohort_code="cohort_group2",
                status=Status.not_actionable,
                reasons=[
                    Reason(
                        rule_type=RuleType.filter,
                        rule_name=RuleName("Exclude is present in sw1"),
                        rule_description=RuleDescription(""),
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    )
                ],
            ),
            CohortResultFactory.build(
                cohort_code="cohort_group3",
                status=Status.not_actionable,
                reasons=[
                    Reason(
                        rule_type=RuleType.filter,
                        rule_name=RuleName("Exclude is present in sw1"),
                        rule_description=None,
                        matcher_matched=False,
                        rule_priority=RulePriority(1),
                    )
                ],
            ),
        ],
    )

    results = build_suitability_results(condition)

    assert_that(
        results,
        contains_exactly(
            is_suitability_rule()
            .with_rule_code("Exclude too young less than 75")
            .and_rule_text("your age is greater than 75")
        ),
    )


def test_no_suitability_rules_for_actionable():
    condition = ConditionFactory.build(status=Status.actionable, cohort_results=[])

    results = build_suitability_results(condition)

    assert_that(results, has_length(0))


@pytest.mark.parametrize(
    ("suggested_actions", "expected"),
    [
        (
            [
                SuggestedAction(
                    action_type=ActionType("TYPE_A"),
                    action_code=ActionCode("CODE123"),
                    action_description=ActionDescription("Some description"),
                    url_link=UrlLink("https://example.com"),
                    url_label=UrlLabel("Learn more"),
                )
            ],
            [
                eligibility_response.Action(
                    actionType=eligibility_response.ActionType("TYPE_A"),
                    actionCode=eligibility_response.ActionCode("CODE123"),
                    description=eligibility_response.Description("Some description"),
                    urlLink=eligibility_response.UrlLink("https://example.com"),
                    urlLabel=eligibility_response.UrlLabel("Learn more"),
                )
            ],
        ),
        (
            [
                SuggestedAction(
                    action_type=ActionType("TYPE_B"),
                    action_code=ActionCode("CODE123"),
                    action_description=None,
                    url_link=None,
                    url_label=None,
                )
            ],
            [
                eligibility_response.Action(
                    actionType=eligibility_response.ActionType("TYPE_B"),
                    actionCode=eligibility_response.ActionCode("CODE123"),
                    description="",
                    urlLink="",
                    urlLabel="",
                )
            ],
        ),
        (
            None,
            None,
        ),
        (
            [],
            [],
        ),
    ],
)
def test_build_actions(suggested_actions, expected):
    results = build_actions(ConditionFactory.build(actions=suggested_actions))
    if expected is None:
        assert_that(results, is_(none()))
    else:
        assert_that(results, contains_exactly(*expected))


def test_excludes_nulls_via_build_response(client: FlaskClient):
    mocked_response = eligibility_response.EligibilityResponse(
        responseId=uuid4(),
        meta=eligibility_response.Meta(lastUpdated=eligibility_response.LastUpdated(datetime(2023, 1, 1, tzinfo=UTC))),
        processedSuggestions=[
            eligibility_response.ProcessedSuggestion(
                condition=eligibility_response.ConditionName("ConditionA"),
                status=eligibility_response.Status.actionable,
                statusText=eligibility_response.StatusText("Go ahead"),
                eligibilityCohorts=[],
                suitabilityRules=[],
                actions=[
                    eligibility_response.Action(
                        actionType=eligibility_response.ActionType("TYPE_A"),
                        actionCode=eligibility_response.ActionCode("CODE123"),
                        description=eligibility_response.Description(""),  # Should be an empty string
                        urlLink=eligibility_response.UrlLink(""),  # Should be an empty string
                        urlLabel=eligibility_response.UrlLabel(""),  # Should be an empty string
                    )
                ],
            )
        ],
    )

    with (
        patch(
            "eligibility_signposting_api.views.eligibility.EligibilityService.get_eligibility_status",
            return_value=MagicMock(),  # No effect
        ),
        patch(
            "eligibility_signposting_api.views.eligibility.AuditService.audit",
            return_value=MagicMock(),  # No effect
        ),
        patch(
            "eligibility_signposting_api.views.eligibility.build_eligibility_response",
            return_value=mocked_response,
        ),
    ):
        response = client.get("/patient-check/12345")
        assert response.status_code == HTTPStatus.OK

        payload = json.loads(response.data)
        suggestion = payload["processedSuggestions"][0]
        action = suggestion["actions"][0]

        assert action["actionType"] == "TYPE_A"
        assert action["actionCode"] == "CODE123"
        assert action["description"] == ""
        assert action["urlLink"] == ""
        assert action["urlLabel"] == ""


def test_build_response_include_values_that_are_not_null(client: FlaskClient):
    mocked_response = eligibility_response.EligibilityResponse(
        responseId=uuid4(),
        meta=eligibility_response.Meta(lastUpdated=eligibility_response.LastUpdated(datetime(2023, 1, 1, tzinfo=UTC))),
        processedSuggestions=[
            eligibility_response.ProcessedSuggestion(
                condition=eligibility_response.ConditionName("ConditionA"),
                status=eligibility_response.Status.actionable,
                statusText=eligibility_response.StatusText("Go ahead"),
                eligibilityCohorts=[],
                suitabilityRules=[],
                actions=[
                    eligibility_response.Action(
                        actionType=eligibility_response.ActionType("TYPE_A"),
                        actionCode=eligibility_response.ActionCode("CODE123"),
                        description=eligibility_response.Description("Contact GP"),
                        urlLink=eligibility_response.UrlLink("https://example.dummy/"),
                        urlLabel=eligibility_response.UrlLabel("GP contact"),
                    )
                ],
            )
        ],
    )

    with (
        patch(
            "eligibility_signposting_api.views.eligibility.EligibilityService.get_eligibility_status",
            return_value=MagicMock(),  # No effect
        ),
        patch(
            "eligibility_signposting_api.views.eligibility.AuditService.audit",
            return_value=MagicMock(),  # No effect
        ),
        patch(
            "eligibility_signposting_api.views.eligibility.build_eligibility_response",
            return_value=mocked_response,
        ),
    ):
        response = client.get("/patient-check/12345")
        assert response.status_code == HTTPStatus.OK

        payload = json.loads(response.data)
        suggestion = payload["processedSuggestions"][0]
        action = suggestion["actions"][0]

        assert action["actionType"] == "TYPE_A"
        assert action["actionCode"] == "CODE123"
        assert action["description"] == "Contact GP"
        assert action["urlLink"] == "https://example.dummy/"
        assert action["urlLabel"] == "GP contact"


@pytest.mark.parametrize(
    ("headers", "expected_request_id"),
    [
        ({"X-Request-ID": "test-request-id-123"}, "test-request-id-123"),
        (
            {"X-Request-ID": ""},
            "",
        ),
        (
            {},  # No headers provided
            None,
        ),
    ],
)
def test_request_id_from_header_logging_variants(
    app: Flask, client: FlaskClient, caplog, headers: dict[str, str], expected_request_id: str
):
    """
    This test checks that the x-request-ID is logged so that it can be used to correlate logs
    with that of the logs from api-gateway
    """
    with (
        get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()),
        get_app_container(app).override.service(AuditService, new=FakeAuditService()),
    ):
        with caplog.at_level(logging.INFO):
            response = client.get("/patient-check/12345", headers=headers)

        request_id_logged = False
        for record in caplog.records:
            request_id = getattr(record, "X-Request-ID", None)

            if request_id == expected_request_id:
                request_id_logged = True
                break

        assert request_id_logged
        assert response.status_code == HTTPStatus.OK


def test_get_or_default_query_params_with_no_args(app: Flask):
    with app.test_request_context("/patient-check"):
        result = get_or_default_query_params()

        expected = {"category": "ALL", "conditions": ["ALL"], "includeActions": "Y"}

        assert_that(result, is_(expected))


def test_get_or_default_query_params_with_all_args(app: Flask):
    with app.test_request_context("/patient-check?includeActions=Y&category=VACCINATIONS&conditions=FLU"):
        result = get_or_default_query_params()

        expected = {"includeActions": "Y", "category": "VACCINATIONS", "conditions": ["FLU"]}

        assert_that(result, is_(expected))


def test_get_or_default_query_params_with_partial_args(app: Flask):
    with app.test_request_context("/patient-check?includeActions=N"):
        result = get_or_default_query_params()

        expected = {"includeActions": "N", "category": "ALL", "conditions": ["ALL"]}

        assert_that(result, is_(expected))


def test_get_or_default_query_params_with_lowercase_y(app: Flask):
    with app.test_request_context("/patient-check?includeActions=y"):
        result = get_or_default_query_params()
        assert_that(result["includeActions"], is_("Y"))


def test_get_or_default_query_params_missing_include_actions(app: Flask):
    with app.test_request_context("/patient-check?category=SCREENING&conditions=COVID19,FLU"):
        result = get_or_default_query_params()

        expected = {"includeActions": "Y", "category": "SCREENING", "conditions": ["COVID19", "FLU"]}

        assert_that(result, is_(expected))
