import json
import logging
from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask import Flask, Request
from flask.testing import FlaskClient
from hamcrest import assert_that, contains_exactly, has_entries, has_length, is_, none
from pydantic import HttpUrl
from wireup.integration.flask import get_app_container

from eligibility_signposting_api.model.eligibility import (
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
    RuleType,
    Status,
    SuggestedAction,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.services.eligibility_services import InvalidQueryParamError
from eligibility_signposting_api.views.eligibility import (
    build_actions,
    build_eligibility_cohorts,
    build_suitability_results,
    get_include_actions_flag,
)
from eligibility_signposting_api.views.response_model import eligibility
from tests.fixtures.builders.model.eligibility import (
    CohortResultFactory,
    ConditionFactory,
    EligibilityStatusFactory,
)
from tests.fixtures.matchers.eligibility import is_eligibility_cohort, is_suitability_rule

logger = logging.getLogger(__name__)


class FakeEligibilityService(EligibilityService):
    def __init__(self):
        pass

    def get_eligibility_status(
        self,
        _: NHSNumber | None = None,
        *,
        include_actions_flag: bool = False,  # noqa: ARG002
    ) -> EligibilityStatus:
        return EligibilityStatusFactory.build()


class FakeUnknownPersonEligibilityService(EligibilityService):
    def __init__(self):
        pass

    def get_eligibility_status(
        self,
        _: NHSNumber | None = None,
        *,
        include_actions_flag: bool = False,  # noqa: ARG002
    ) -> EligibilityStatus:
        raise UnknownPersonError


class FakeUnexpectedErrorEligibilityService(EligibilityService):
    def __init__(self):
        pass

    def get_eligibility_status(
        self,
        _: NHSNumber | None = None,
        *,
        include_actions_flag: bool = False,  # noqa: ARG002
    ) -> EligibilityStatus:
        raise ValueError


def test_nhs_number_given(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()):
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
        .and_text(
            is_json_that(
                has_entries(
                    resourceType="OperationOutcome",
                    issue=contains_exactly(
                        has_entries(
                            severity="information", code="nhs-number-not-found", diagnostics='NHS Number "" not found.'
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
            .and_text(
                is_json_that(
                    has_entries(
                        resourceType="OperationOutcome",
                        issue=contains_exactly(has_entries(severity="severe", code="unexpected")),
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
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude too young less than 75"),
                        rule_description=RuleDescription("your age is greater than 75"),
                        matcher_matched=False,
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude more than 100"),
                        rule_description=RuleDescription("your age is greater than 100"),
                        matcher_matched=False,
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
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude more than 100"),
                        rule_description=RuleDescription(""),
                        matcher_matched=False,
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude more than 100"),
                        matcher_matched=False,
                        rule_description=None,
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
                eligibility.Action(
                    actionType=eligibility.ActionType("TYPE_A"),
                    actionCode=eligibility.ActionCode("CODE123"),
                    description=eligibility.Description("Some description"),
                    urlLink=eligibility.HttpUrl("https://example.com"),
                    urlLabel=eligibility.UrlLabel("Learn more"),
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
                eligibility.Action(
                    actionType=eligibility.ActionType("TYPE_B"),
                    actionCode=eligibility.ActionCode("CODE123"),
                    description=None,
                    urlLink=None,
                    urlLabel=None,
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


def test_nhs_number_and_include_actions_param_given_and_is_yes(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()):
        # When
        response = client.get("/patient-check/12345?includeActions=Y")

        # Then
        assert_that(response, is_response().with_status_code(HTTPStatus.OK))


def test_nhs_number_and_include_actions_param_no_given(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()):
        # When
        response = client.get("/patient-check/12345?includeActions=N")

        # Then
        assert_that(response, is_response().with_status_code(HTTPStatus.OK))


def test_nhs_number_and_include_actions_param_value_is_incorrect(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()):
        # When
        response = client.get("/patient-check/12345?includeActions=abc")

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.BAD_REQUEST)
            .and_text(
                is_json_that(
                    has_entries(
                        resourceType="OperationOutcome",
                        issue=contains_exactly(
                            has_entries(
                                severity="error", code="invalid", diagnostics="Invalid query param key or value."
                            )
                        ),
                    )
                )
            ),
        )


def test_nhs_number_and_unrecognised_query_param_provided(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()):
        # When
        response = client.get("/patient-check/12345?example-key=example-value")

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.BAD_REQUEST)
            .and_text(
                is_json_that(
                    has_entries(
                        resourceType="OperationOutcome",
                        issue=contains_exactly(
                            has_entries(
                                severity="error", code="invalid", diagnostics="Invalid query param key or value."
                            )
                        ),
                    )
                )
            ),
        )


def test_query_param_include_actions_flag_with_yes():
    # Given:
    mock_request = Mock(spec=Request)
    mock_request.args = {"includeActions": "Y"}
    with patch("eligibility_signposting_api.views.eligibility.request", mock_request):
        # When:
        result = get_include_actions_flag()

    # Then:
    assert result is True


def test_query_param_include_actions_flag_with_no():
    # Given:
    mock_request = Mock(spec=Request)
    mock_request.args = {"includeActions": "N"}
    with patch("eligibility_signposting_api.views.eligibility.request", mock_request):
        # When:
        result = get_include_actions_flag()

    # Then:
    assert result is False


def test_query_param_include_actions_flag_with_no_param():
    # Given:
    mock_request = Mock(spec=Request)
    mock_request.args = {}
    with patch("eligibility_signposting_api.views.eligibility.request", mock_request):
        # When:
        result = get_include_actions_flag()

    # Then:
    assert result is True


def test_query_param_include_actions_flag_with_invalid_value():
    # Given:
    mock_request = Mock(spec=Request)
    mock_request.args = {"includeActions": "invalid"}
    with (
        patch("eligibility_signposting_api.views.eligibility.request", mock_request),
        pytest.raises(InvalidQueryParamError),
    ):
        get_include_actions_flag()


def test_query_param_include_actions_flag_with_other_params():
    # Given:
    mock_request = Mock(spec=Request)
    mock_request.args = {"otherParam": "value"}
    with (
        patch("eligibility_signposting_api.views.eligibility.request", mock_request),
        pytest.raises(InvalidQueryParamError),
    ):
        get_include_actions_flag()


def test_excludes_nulls_via_build_response(client: FlaskClient):
    mocked_response = eligibility.EligibilityResponse(
        responseId=uuid4(),
        meta=eligibility.Meta(lastUpdated=eligibility.LastUpdated(datetime(2023, 1, 1, tzinfo=UTC))),
        processedSuggestions=[
            eligibility.ProcessedSuggestion(
                condition=eligibility.ConditionName("ConditionA"),
                status=eligibility.Status.actionable,
                statusText=eligibility.StatusText("Go ahead"),
                eligibilityCohorts=[],
                suitabilityRules=[],
                actions=[
                    eligibility.Action(
                        actionType=eligibility.ActionType("TYPE_A"),
                        actionCode=eligibility.ActionCode("CODE123"),
                        description=None,  # Should be excluded
                        urlLink=None,  # Should be excluded
                        urlLabel=None,  # Should be excluded
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
        assert "description" not in action
        assert "urlLink" not in action
        assert "urlLabel" not in action


def test_build_response_include_values_that_are_not_null(client: FlaskClient):
    mocked_response = eligibility.EligibilityResponse(
        responseId=uuid4(),
        meta=eligibility.Meta(lastUpdated=eligibility.LastUpdated(datetime(2023, 1, 1, tzinfo=UTC))),
        processedSuggestions=[
            eligibility.ProcessedSuggestion(
                condition=eligibility.ConditionName("ConditionA"),
                status=eligibility.Status.actionable,
                statusText=eligibility.StatusText("Go ahead"),
                eligibilityCohorts=[],
                suitabilityRules=[],
                actions=[
                    eligibility.Action(
                        actionType=eligibility.ActionType("TYPE_A"),
                        actionCode=eligibility.ActionCode("CODE123"),
                        description=eligibility.Description("Contact GP"),
                        urlLink=eligibility.HttpUrl(HttpUrl("https://example.dummy/")),
                        urlLabel=eligibility.UrlLabel("GP contact"),
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
