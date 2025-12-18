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
from tests.fixtures.matchers.eligibility import is_eligibility_cohort

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
        _consumer_id: str,
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
        _consumer_id: str,
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


def test_security_headers_present_on_successful_response(app: Flask, client: FlaskClient):
    """Test that security headers are present on successful eligibility check response."""
    # Given
    with (
        get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()),
        get_app_container(app).override.service(AuditService, new=FakeAuditService()),
    ):
        # When
        headers = {"nhs-login-nhs-number": "9876543210", "Consumer-Id": "test_consumer_id"}
        response = client.get("/patient-check/9876543210", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .with_headers(
                has_entries(
                    {
                        "Cache-Control": "no-store, private",
                        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                        "X-Content-Type-Options": "nosniff",
                    }
                )
            ),
        )


def test_security_headers_present_on_error_response(app: Flask, client: FlaskClient):
    """Test that security headers are present on error response."""
    # Given
    with (
        get_app_container(app).override.service(EligibilityService, new=FakeUnknownPersonEligibilityService()),
        get_app_container(app).override.service(AuditService, new=FakeAuditService()),
    ):
        # When
        headers = {"nhs-login-nhs-number": "9876543210"}
        response = client.get("/patient-check/9876543210", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.NOT_FOUND)
            .with_headers(
                has_entries(
                    {
                        "Cache-Control": "no-store, private",
                        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                        "X-Content-Type-Options": "nosniff",
                    }
                )
            ),
        )


def test_security_headers_present_on_status_endpoint(client: FlaskClient):
    """Test that security headers are present on health check endpoint."""
    # When
    response = client.get("/patient-check/_status")

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.OK)
        .with_headers(
            has_entries(
                {
                    "Cache-Control": "no-store, private",
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    "X-Content-Type-Options": "nosniff",
                }
            )
        ),
    )


def test_nhs_number_given(app: Flask, client: FlaskClient):
    # Given
    with (
        get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()),
        get_app_container(app).override.service(AuditService, new=FakeAuditService()),
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(12345)}

        # When
        response = client.get("/patient-check/12345", headers=headers)

        # Then
        assert_that(response, is_response().with_status_code(HTTPStatus.OK))


def test_no_nhs_number_given(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeUnknownPersonEligibilityService()):
        # Given
        headers = {"nhs-login-nhs-number": str(12345)}

        # When
        response = client.get("/patient-check/", headers=headers)

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.FORBIDDEN)
        .with_headers(has_entries({"Content-Type": "application/fhir+json"}))
        .and_text(
            is_json_that(
                has_entries(
                    resourceType="OperationOutcome",
                    issue=contains_exactly(
                        has_entries(
                            severity="error",
                            code="forbidden",
                            diagnostics="You are not authorised to request information for the supplied NHS Number",
                            details={
                                "coding": [
                                    {
                                        "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                        "code": "ACCESS_DENIED",
                                        "display": "Access has been denied to process this request.",
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
    headers = {"nhs-login-nhs-number": str(12345)}

    with get_app_container(app).override.service(EligibilityService, new=FakeUnexpectedErrorEligibilityService()):
        response = client.get("/patient-check/12345", headers=headers)

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
        response = client.get("/patient-check/12345", headers={"nhs-login-nhs-number": str(12345)})
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
        response = client.get("/patient-check/12345", headers={"nhs-login-nhs-number": str(12345)})
        assert response.status_code == HTTPStatus.OK

        payload = json.loads(response.data)
        suggestion = payload["processedSuggestions"][0]
        action = suggestion["actions"][0]

        assert action["actionType"] == "TYPE_A"
        assert action["actionCode"] == "CODE123"
        assert action["description"] == "Contact GP"
        assert action["urlLink"] == "https://example.dummy/"
        assert action["urlLabel"] == "GP contact"


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


def test_status_endpoint(app: Flask, client: FlaskClient):
    with get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()):
        response = client.get("/patient-check/_status")

        assert_that(response, is_response().with_status_code(HTTPStatus.OK))

        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .with_headers(has_entries({"Content-Type": "application/json"}))
            .and_json(
                has_entries(
                    {
                        "status": "pass",
                        "checks": has_entries(
                            {
                                "healthcheckService:status": contains_exactly(
                                    has_entries(
                                        {
                                            "status": "pass",
                                            "timeout": False,
                                            "responseCode": HTTPStatus.OK,
                                            "outcome": "<html><h1>Ok</h1></html>",
                                            "links": has_entries({"self": "https://localhost/patient-check/_status"}),
                                        }
                                    )
                                )
                            }
                        ),
                    }
                )
            ),
        )
