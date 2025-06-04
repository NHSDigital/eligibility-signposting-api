from http import HTTPStatus

from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask.testing import FlaskClient
from hamcrest import assert_that, has_entries, has_entry, has_item, has_key

from eligibility_signposting_api.model.eligibility import NHSNumber
from eligibility_signposting_api.model.rules import CampaignConfig


def test_nhs_number_given(client: FlaskClient, persisted_person: NHSNumber, campaign_config: CampaignConfig):  # noqa: ARG001
    # Given

    # When
    response = client.get(f"/patient-check/{persisted_person}")

    # Then
    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_text(is_json_that(has_key("processedSuggestions"))),
    )


def test_no_nhs_number_given(client: FlaskClient):
    # Given

    # When
    response = client.get("/patient-check/")

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.NOT_FOUND)
        .and_text(is_json_that(has_entries(resourceType="OperationOutcome"))),
    )


def test_not_base_eligible(client: FlaskClient, persisted_person_no_cohorts: NHSNumber, campaign_config: CampaignConfig):  # noqa: ARG001
    # Given

    # When
    response = client.get(f"/patient-check/{persisted_person_no_cohorts}")

    print("here is the respose")
    print(response.text)

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.OK)
        .and_text(
            is_json_that(
                has_entry("processedSuggestions", has_item(has_entries(condition="RSV", status="NotEligible")))
            )
        ),
    )

def test_not_eligible_by_rule(client: FlaskClient, persisted_person_pc_sw19: NHSNumber, campaign_config: CampaignConfig):  # noqa: ARG001
    # Given

    # When
    response = client.get(f"/patient-check/{persisted_person_pc_sw19}")

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.OK)
        .and_text(
            is_json_that(
                has_entry("processedSuggestions", has_item(has_entries(condition="RSV", status="NotEligible")))
            )
        ),
    )


def test_not_actionable_by_rule(client: FlaskClient, persisted_person: NHSNumber, campaign_config: CampaignConfig):  # noqa: ARG001
    # Given

    # When
    response = client.get(f"/patient-check/{persisted_person}")

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.OK)
        .and_text(
            is_json_that(
                has_entry("processedSuggestions", has_item(has_entries(condition="RSV", status="NotActionable")))
            )
        ),
    )


def test_actionable_by_rule(client: FlaskClient, persisted_77yo_person: NHSNumber, campaign_config: CampaignConfig):  # noqa: ARG001
    # Given

    # When
    response = client.get(f"/patient-check/{persisted_77yo_person}")

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.OK)
        .and_text(
            is_json_that(has_entry("processedSuggestions", has_item(has_entries(condition="RSV", status="Actionable"))))
        ),
    )



