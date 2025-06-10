import logging
from http import HTTPStatus

import pytest
from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask import Flask
from flask.testing import FlaskClient
from hamcrest import assert_that, contains_exactly, has_entries, has_key, has_length
from wireup.integration.flask import get_app_container

from eligibility_signposting_api.model.eligibility import (
    CohortResult,
    Condition,
    EligibilityStatus,
    NHSNumber,
    Reason,
    RuleName,
    RuleResult,
    RuleType,
    Status,
)
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.views.eligibility import (
    build_eligibility_cohorts,
    build_suitability_results,
)
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

    def get_eligibility_status(self, _: NHSNumber | None = None) -> EligibilityStatus:
        return EligibilityStatusFactory.build()


class FakeUnknownPersonEligibilityService(EligibilityService):
    def __init__(self):
        pass

    def get_eligibility_status(self, _: NHSNumber | None = None) -> EligibilityStatus:
        raise UnknownPersonError


class FakeUnexpectedErrorEligibilityService(EligibilityService):
    def __init__(self):
        pass

    def get_eligibility_status(self, _: NHSNumber | None = None) -> EligibilityStatus:
        raise ValueError


def test_nhs_number_given(app: Flask, client: FlaskClient):
    # Given
    with get_app_container(app).override.service(EligibilityService, new=FakeEligibilityService()):
        # When
        response = client.get("/patient-check/12345")

        # Then
    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_text(is_json_that(has_key("processedSuggestions"))),
    )


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
            "two cohort group codes with same status",
        ),
        (
            [
                CohortResultFactory.build(cohort_code="", status=Status.not_actionable, description=""),
            ],
            [],
            "no cohort code, i.e only magic cohort is present, so no eligibility cohort is populated",
        ),
    ],
)
def test_build_eligibility_cohorts_results_consider_only_cohorts_that_has_cohort_label(
    cohort_results: list[CohortResult], expected_eligibility_cohorts: list[tuple[str, str, str]], test_comment
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
                        rule_result=RuleResult("Age < 75"),
                    ),
                    Reason(
                        rule_type=RuleType.suppression,
                        rule_name=RuleName("Exclude more than 100"),
                        rule_result=RuleResult("Age > 100"),
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
                        rule_result=RuleResult("Age < 75"),
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
                        rule_result=RuleResult("memberof sw1"),
                    )
                ],
            ),
        ],
    )

    results = build_suitability_results(condition)

    assert_that(
        results,
        contains_exactly(
            is_suitability_rule().with_rule_code("Exclude too young less than 75").and_rule_text("Age < 75"),
            is_suitability_rule().with_rule_code("Exclude more than 100").and_rule_text("Age > 100"),
        ),
    )


def test_no_suitability_rules_for_actionable():
    condition = ConditionFactory.build(status=Status.actionable, cohort_results=[])

    results = build_suitability_results(condition)

    assert_that(results, has_length(0))
