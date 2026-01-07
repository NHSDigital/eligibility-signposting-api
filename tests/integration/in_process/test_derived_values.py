"""
Integration tests for derived values functionality.

These tests verify the end-to-end flow of the ADD_DAYS derived value function,
demonstrating how NEXT_DOSE_DUE is calculated from LAST_SUCCESSFUL_DATE.

Example API response format:
{
    "processedSuggestions": [
        {
            "actions": [
                {
                    "actionType": "DataValue",
                    "actionCode": "DateOfLastVaccination",
                    "description": "20260128"
                },
                {
                    "actionType": "DataValue",
                    "actionCode": "DateOfNextEarliestVaccination",
                    "description": "20260429"
                }
            ]
        }
    ]
}
"""

from http import HTTPStatus

from botocore.client import BaseClient
from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask.testing import FlaskClient
from hamcrest import (
    assert_that,
    greater_than_or_equal_to,
    has_entries,
    has_item,
    has_key,
    has_length,
    is_not,
    none,
)

from eligibility_signposting_api.model.campaign_config import CampaignConfig
from eligibility_signposting_api.model.eligibility_status import NHSNumber


class TestDerivedValues:
    """Integration tests for the ADD_DAYS derived value functionality."""

    def test_add_days_calculates_next_dose_due_from_last_successful_date(
        self,
        client: FlaskClient,
        person_with_covid_vaccination: NHSNumber,
        campaign_config_with_derived_values: CampaignConfig,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        """
        Test that the ADD_DAYS function correctly calculates the next dose date.

        Given:
            - A person with COVID vaccination on 2026-01-28 (20260128)
            - A campaign config with actions using:
                - [[TARGET.COVID.LAST_SUCCESSFUL_DATE]] for DateOfLastVaccination
                - [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]] for DateOfNextEarliestVaccination

        Expected:
            - DateOfLastVaccination shows "20260128"
            - DateOfNextEarliestVaccination shows "20260429" (2026-01-28 + 91 days = 2026-04-29)

        This demonstrates the use case from the requirement:
            "actions": [
                {"actionType": "DataValue", "actionCode": "DateOfLastVaccination", "description": "20260128"},
                {"actionType": "DataValue", "actionCode": "DateOfNextEarliestVaccination", "description": "20260429"}
            ]
        """
        # Given
        headers = {"nhs-login-nhs-number": str(person_with_covid_vaccination)}

        # When
        response = client.get(
            f"/patient-check/{person_with_covid_vaccination}?includeActions=Y",
            headers=headers,
        )

        # Then - verify response is successful
        assert_that(
            response,
            is_response().with_status_code(HTTPStatus.OK).and_text(is_json_that(has_key("processedSuggestions"))),
        )

        # Extract the processed suggestions
        body = response.get_json()
        assert_that(body, is_not(none()))
        processed_suggestions = body.get("processedSuggestions", [])

        # Find the COVID condition
        covid_suggestion = next(
            (s for s in processed_suggestions if s.get("condition") == "COVID"),
            None,
        )
        assert_that(covid_suggestion, is_not(none()))

        # Extract actions
        actions = covid_suggestion.get("actions", [])  # type: ignore[union-attr]
        expected_actions_count = 2
        assert_that(actions, has_length(greater_than_or_equal_to(expected_actions_count)))

        # Verify DateOfLastVaccination shows the raw date
        assert_that(
            actions,
            has_item(has_entries(actionType="DataValue", actionCode="DateOfLastVaccination", description="20260128")),
        )

        # Verify DateOfNextEarliestVaccination shows the calculated date (2026-01-28 + 91 days = 2026-04-29)
        assert_that(
            actions,
            has_item(
                has_entries(actionType="DataValue", actionCode="DateOfNextEarliestVaccination", description="20260429")
            ),
        )

    def test_add_days_with_formatted_date_output(
        self,
        client: FlaskClient,
        person_with_covid_vaccination: NHSNumber,
        campaign_config_with_derived_values_formatted: CampaignConfig,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        """
        Test that ADD_DAYS can be combined with DATE formatting.

        Given:
            - A person with COVID vaccination on 2026-01-28
            - A campaign config using [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91):DATE(%d %B %Y)]]

        Expected:
            - DateOfNextEarliestVaccination shows "29 April 2026" (formatted output)
        """
        # Given
        headers = {"nhs-login-nhs-number": str(person_with_covid_vaccination)}

        # When
        response = client.get(
            f"/patient-check/{person_with_covid_vaccination}?includeActions=Y",
            headers=headers,
        )

        # Then
        assert_that(
            response,
            is_response().with_status_code(HTTPStatus.OK).and_text(is_json_that(has_key("processedSuggestions"))),
        )

        body = response.get_json()
        assert_that(body, is_not(none()))
        processed_suggestions = body.get("processedSuggestions", [])

        covid_suggestion = next(
            (s for s in processed_suggestions if s.get("condition") == "COVID"),
            None,
        )
        assert_that(covid_suggestion, is_not(none()))

        actions = covid_suggestion.get("actions", [])  # type: ignore[union-attr]

        # Verify the formatted date output
        assert_that(
            actions,
            has_item(has_entries(actionCode="DateOfNextEarliestVaccination", description="29 April 2026")),
        )
