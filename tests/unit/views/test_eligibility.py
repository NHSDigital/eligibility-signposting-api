import logging
from http import HTTPStatus

from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask import Flask
from flask.testing import FlaskClient
from hamcrest import assert_that, contains_exactly, has_entries, has_key, has_length
from wireup.integration.flask import get_app_container

from eligibility_signposting_api.model.eligibility import (
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
from tests.fixtures.builders.model.eligibility import CohortResultFactory, ConditionFactory, EligibilityStatusFactory
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


def test_build_eligibility_cohorts_results_consider_only_cohorts_with_best_status():
    condition: Condition = ConditionFactory.build(
        status=Status.not_actionable,
        cohort_results=[
            CohortResultFactory.build(
                cohort_code="cohort_group1",
                status=Status.not_actionable,
            ),
            CohortResultFactory.build(
                cohort_code="cohort_group2",
                status=Status.not_eligible,
            ),
        ],
    )

    results = build_eligibility_cohorts(condition)

    assert_that(
        results,
        contains_exactly(is_eligibility_cohort().with_cohort_code("cohort_group1").and_cohort_status("NotActionable")),
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
