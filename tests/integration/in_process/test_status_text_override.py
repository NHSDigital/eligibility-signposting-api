from http import HTTPStatus

from botocore.client import BaseClient
from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask.testing import FlaskClient
from hamcrest import assert_that, has_entries, has_item, has_key, is_not, none

from eligibility_signposting_api.model.consumer_mapping import ConsumerId, ConsumerMapping
from eligibility_signposting_api.model.eligibility_status import NHSNumber
from tests.integration.conftest import UNIQUE_CONSUMER_HEADER


class TestStatusTextOverride:
    def test_status_text_override_replaces_iteration_status_text_and_is_not_returned_as_action(
        self,
        client: FlaskClient,
        person_with_covid_vaccination: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_campaign_config_with_status_text_override_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        headers = {
            "nhs-login-nhs-number": str(person_with_covid_vaccination),
            UNIQUE_CONSUMER_HEADER: str(consumer_id),
        }

        response = client.get(
            f"/patient-check/{person_with_covid_vaccination}?includeActions=Y",
            headers=headers,
        )

        assert_that(
            response,
            is_response().with_status_code(HTTPStatus.OK).and_text(is_json_that(has_key("processedSuggestions"))),
        )

        body = response.get_json()
        assert_that(body, is_not(none()))
        processed_suggestions = body.get("processedSuggestions", [])

        covid_suggestion = next(
            (suggestion for suggestion in processed_suggestions if suggestion.get("condition") == "COVID"),
            None,
        )
        assert_that(covid_suggestion, is_not(none()))
        assert covid_suggestion["status"] == "Actionable"
        assert covid_suggestion["statusText"] == "Overridden actionable status text"

        actions = covid_suggestion.get("actions", [])
        assert_that(
            actions,
            has_item(
                has_entries(
                    actionType="DataValue",
                    actionCode="VisibleAction",
                    description="Visible action description",
                )
            ),
        )
        assert all(action.get("actionType") != "norender_StatusTextOverride" for action in actions)