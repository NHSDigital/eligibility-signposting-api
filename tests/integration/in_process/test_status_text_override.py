import json
from http import HTTPStatus

from botocore.client import BaseClient
from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask.testing import FlaskClient
from hamcrest import assert_that, has_entries, has_item, has_key, is_not, none, equal_to, is_

from eligibility_signposting_api.model.consumer_mapping import ConsumerId, ConsumerMapping
from eligibility_signposting_api.model.eligibility_status import NHSNumber
from tests.integration.conftest import UNIQUE_CONSUMER_HEADER, bridge_latest_kinesis_record_to_firehose

from eligibility_signposting_api.repos.campaign_repo import BucketName


class TestStatusTextOverride:
    def test_status_text_override_replaces_iteration_status_text_and_is_not_returned_as_action(
        self,
        client: FlaskClient,
        audit_bucket: BucketName,
        s3_client: BaseClient,
        person_with_covid_vaccination: NHSNumber,
        consumer_id: ConsumerId,
        kinesis_client,
        firehose_client,
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

        bridge_latest_kinesis_record_to_firehose(
            kinesis_client=kinesis_client,
            kinesis_stream_name="test-kinesis-audit-stream",
            firehose_client=firehose_client,
            firehose_delivery_stream_name="test_firehose_audit_stream_to_s3",
        )

        # Then
        objects = s3_client.list_objects_v2(Bucket=audit_bucket).get("Contents", [])
        object_keys = [obj["Key"] for obj in objects]
        latest_key = sorted(object_keys)[-1]
        audit_data = json.loads(s3_client.get_object(Bucket=audit_bucket, Key=latest_key)["Body"].read())

        status_text_override = "Overridden actionable status text"
        status_text = "Overridden actionable status text"

        assert_that(len(audit_data["response"]["condition"]), equal_to(1))
        assert_that(audit_data["response"]["condition"][0].get("statusTextOverride"), equal_to(status_text_override))
        assert_that(audit_data["response"]["condition"][0].get("statusText"), equal_to(status_text))

    def test_no_status_text_override_as_no_action(
        self,
        client: FlaskClient,
        audit_bucket: BucketName,
        s3_client: BaseClient,
        person_with_covid_vaccination: NHSNumber,
        consumer_id: ConsumerId,
        kinesis_client,
        firehose_client,
        consumer_to_active_campaign_config_with_status_text_override_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        headers = {
            "nhs-login-nhs-number": str(person_with_covid_vaccination),
            UNIQUE_CONSUMER_HEADER: str(consumer_id),
        }

        response = client.get(
            f"/patient-check/{person_with_covid_vaccination}?includeActions=N",
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
        assert covid_suggestion["statusText"] == "Original actionable text"

        actions = covid_suggestion.get("actions", [])

        assert_that(actions,is_([]))

        assert all(action.get("actionType") != "norender_StatusTextOverride" for action in actions)

        bridge_latest_kinesis_record_to_firehose(
            kinesis_client=kinesis_client,
            kinesis_stream_name="test-kinesis-audit-stream",
            firehose_client=firehose_client,
            firehose_delivery_stream_name="test_firehose_audit_stream_to_s3",
        )

        # Then
        objects = s3_client.list_objects_v2(Bucket=audit_bucket).get("Contents", [])
        object_keys = [obj["Key"] for obj in objects]
        latest_key = sorted(object_keys)[-1]
        audit_data = json.loads(s3_client.get_object(Bucket=audit_bucket, Key=latest_key)["Body"].read())

        status_text_override = None
        status_text = "Original actionable text"

        assert_that(len(audit_data["response"]["condition"]), equal_to(1))
        assert_that(audit_data["response"]["condition"][0].get("statusTextOverride"), equal_to(status_text_override))
        assert_that(audit_data["response"]["condition"][0].get("statusText"), equal_to(status_text))