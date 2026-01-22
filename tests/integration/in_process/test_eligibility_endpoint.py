import json
from http import HTTPStatus

import pytest
from botocore.client import BaseClient
from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask.testing import FlaskClient
from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_entry,
    has_key,
)

from eligibility_signposting_api.model.campaign_config import CampaignConfig, RuleComparator
from eligibility_signposting_api.model.consumer_mapping import ConsumerId, ConsumerMapping
from eligibility_signposting_api.model.eligibility_status import (
    NHSNumber,
)
from eligibility_signposting_api.repos.campaign_repo import BucketName
from tests.fixtures.builders.model import rule


class TestBaseLine:
    def test_nhs_number_given(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_rsv_campaign_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person}", headers=headers)

        # Then
        assert_that(
            response,
            is_response().with_status_code(HTTPStatus.OK).and_text(is_json_that(has_key("processedSuggestions"))),
        )

    @pytest.mark.parametrize(
        "headers",
        [
            {},  # header missing entirely, valid
        ],
    )
    def test_nhs_number_given_in_path_but_no_nhs_number_header_present(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_to_active_rsv_campaign_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
        headers: dict,
    ):
        # Given
        # When
        response = client.get(f"/patient-check/{persisted_person}", headers={"consumer-id": "some-id"} | headers)

        # Then
        assert_that(
            response,
            is_response().with_status_code(HTTPStatus.OK).and_text(is_json_that(has_key("processedSuggestions"))),
        )

    @pytest.mark.parametrize(
        "headers",
        [
            {"nhs-login-nhs-number": None},  # header present but empty, invalid
            {"nhs-login-nhs-number": ""},  # header present but blank, invalid
        ],
    )
    def test_nhs_number_in_path_and_header_present_but_empty_or_none(  # noqa: PLR0913
        self,
        headers: dict,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_rsv_campaign_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # When
        response = client.get(f"/patient-check/{persisted_person}", headers={"consumer-id": consumer_id} | headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.FORBIDDEN)
            .and_text(is_json_that(has_entries(resourceType="OperationOutcome"))),
        )

    def test_nhs_number_given_but_header_nhs_number_doesnt_match(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_rsv_campaign_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": f"123{persisted_person!s}"}

        # When
        response = client.get(f"/patient-check/{persisted_person}", headers={"consumer-id": consumer_id} | headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.FORBIDDEN)
            .and_text(is_json_that(has_entries(resourceType="OperationOutcome"))),
        )

    def test_no_nhs_number_given(self, client: FlaskClient):
        # Given

        # When
        response = client.get("/patient-check/")

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.FORBIDDEN)
            .and_text(is_json_that(has_entries(resourceType="OperationOutcome"))),
        )

    def test_no_nhs_number_given_but_header_given(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person)}

        # When
        response = client.get("/patient-check/", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.FORBIDDEN)
            .and_text(is_json_that(has_entries(resourceType="OperationOutcome"))),
        )


class TestStandardResponse:
    def test_not_base_eligible(
        self,
        client: FlaskClient,
        persisted_person_no_cohorts: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_rsv_campaign_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_no_cohorts), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person_no_cohorts}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "RSV",
                                    "status": "NotEligible",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "cohort_group1",
                                            "cohortStatus": "NotEligible",
                                            "cohortText": "negative_description",
                                        }
                                    ],
                                    "actions": [],
                                    "suitabilityRules": [],
                                    "statusText": "We do not believe you can have it",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_not_eligible_by_rule(
        self,
        client: FlaskClient,
        persisted_person_pc_sw19: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_rsv_campaign_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person_pc_sw19}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "RSV",
                                    "status": "NotEligible",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "cohort_group1",
                                            "cohortStatus": "NotEligible",
                                            "cohortText": "negative_description",
                                        }
                                    ],
                                    "actions": [],
                                    "suitabilityRules": [],
                                    "statusText": "We do not believe you can have it",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_not_actionable_and_check_response_when_no_rule_code_given(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_rsv_campaign_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "RSV",
                                    "status": "NotActionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "cohort_group1",
                                            "cohortStatus": "NotActionable",
                                            "cohortText": "positive_description",
                                        }
                                    ],
                                    "actions": [],
                                    "suitabilityRules": [
                                        {
                                            "ruleCode": "Exclude too young less than 75",
                                            "ruleText": "Exclude too young less than 75",
                                            "ruleType": "S",
                                        }
                                    ],
                                    "statusText": "You should have the RSV vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_actionable(
        self,
        client: FlaskClient,
        persisted_77yo_person: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_rsv_campaign_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_77yo_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "RSV",
                                    "status": "Actionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "cohort_group1",
                                            "cohortStatus": "Actionable",
                                            "cohortText": "positive_description",
                                        }
                                    ],
                                    "actions": [
                                        {
                                            "actionCode": "action_code",
                                            "actionType": "defaultcomms",
                                            "description": "",
                                            "urlLabel": "",
                                            "urlLink": "",
                                        }
                                    ],
                                    "suitabilityRules": [],
                                    "statusText": "You should have the RSV vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_actionable_with_and_rule(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_id: ConsumerId,
        consumer_to_active_campaign_having_and_rule_mapping: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "RSV",
                                    "status": "Actionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "cohort_group1",
                                            "cohortStatus": "Actionable",
                                            "cohortText": "positive_description",
                                        }
                                    ],
                                    "actions": [
                                        {
                                            "actionCode": "action_code",
                                            "actionType": "defaultcomms",
                                            "description": "",
                                            "urlLabel": "",
                                            "urlLink": "",
                                        }
                                    ],
                                    "suitabilityRules": [],
                                    "statusText": "You should have the RSV vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )


class TestVirtualCohortResponse:
    def test_not_eligible_by_rule_when_only_virtual_cohort_is_present(
        self,
        client: FlaskClient,
        persisted_person_pc_sw19: NHSNumber,
        consumer_to_active_campaign_having_only_virtual_cohort_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person_pc_sw19}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "COVID",
                                    "status": "NotEligible",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "virtual cohort group",
                                            "cohortStatus": "NotEligible",
                                            "cohortText": "virtual negative description",
                                        }
                                    ],
                                    "actions": [],
                                    "suitabilityRules": [],
                                    "statusText": "We do not believe you can have it",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_not_actionable_when_only_virtual_cohort_is_present(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_to_active_campaign_having_only_virtual_cohort_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "COVID",
                                    "status": "NotActionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "virtual cohort group",
                                            "cohortStatus": "NotActionable",
                                            "cohortText": "virtual positive description",
                                        }
                                    ],
                                    "actions": [],
                                    "suitabilityRules": [
                                        {
                                            "ruleCode": "Exclude too young less than 75",
                                            "ruleText": "Exclude too young less than 75",
                                            "ruleType": "S",
                                        }
                                    ],
                                    "statusText": "You should have the COVID vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_actionable_when_only_virtual_cohort_is_present(
        self,
        client: FlaskClient,
        persisted_77yo_person: NHSNumber,
        consumer_to_active_campaign_having_only_virtual_cohort_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_77yo_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "COVID",
                                    "status": "Actionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "virtual cohort group",
                                            "cohortStatus": "Actionable",
                                            "cohortText": "virtual positive description",
                                        }
                                    ],
                                    "actions": [
                                        {
                                            "actionCode": "action_code",
                                            "actionType": "defaultcomms",
                                            "description": "",
                                            "urlLabel": "",
                                            "urlLink": "",
                                        }
                                    ],
                                    "suitabilityRules": [],
                                    "statusText": "You should have the COVID vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )


class TestResponseOnMissingAttributes:
    def test_not_base_eligible(
        self,
        client: FlaskClient,
        persisted_person_no_cohorts: NHSNumber,
        consumer_to_active_campaign_missing_descriptions_and_rule_text_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_no_cohorts), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person_no_cohorts}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "FLU",
                                    "status": "NotEligible",
                                    "eligibilityCohorts": [],
                                    "actions": [],
                                    "suitabilityRules": [],
                                    "statusText": "We do not believe you can have it",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_not_eligible_by_rule(
        self,
        client: FlaskClient,
        persisted_person_pc_sw19: NHSNumber,
        consumer_to_active_campaign_missing_descriptions_and_rule_text_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person_pc_sw19}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "FLU",
                                    "status": "NotEligible",
                                    "eligibilityCohorts": [],
                                    "actions": [],
                                    "suitabilityRules": [],
                                    "statusText": "We do not believe you can have it",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_not_actionable(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_to_active_campaign_missing_descriptions_and_rule_text_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "FLU",
                                    "status": "NotActionable",
                                    "eligibilityCohorts": [],
                                    "actions": [],
                                    "suitabilityRules": [
                                        {
                                            "ruleCode": "Exclude too young less than 75",
                                            "ruleText": "Exclude too young less than 75",
                                            "ruleType": "S",
                                        }
                                    ],
                                    "statusText": "You should have the FLU vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_actionable(
        self,
        client: FlaskClient,
        persisted_77yo_person: NHSNumber,
        consumer_to_active_campaign_missing_descriptions_and_rule_text_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_77yo_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "FLU",
                                    "status": "Actionable",
                                    "eligibilityCohorts": [],
                                    "actions": [
                                        {
                                            "actionCode": "action_code",
                                            "actionType": "defaultcomms",
                                            "description": "",
                                            "urlLabel": "",
                                            "urlLink": "",
                                        }
                                    ],
                                    "suitabilityRules": [],
                                    "statusText": "You should have the FLU vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_actionable_no_actions(
        self,
        client: FlaskClient,
        persisted_77yo_person: NHSNumber,
        consumer_to_active_campaign_missing_descriptions_and_rule_text_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_77yo_person}?includeActions=N", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "FLU",
                                    "status": "Actionable",
                                    "eligibilityCohorts": [],
                                    "suitabilityRules": [],
                                    "statusText": "You should have the FLU vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_status_endpoint(self, client: FlaskClient):
        # When
        response = client.get("/patient-check/_status")

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
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

        assert_that(response.headers, has_entry("Content-Type", "application/json"))


class TestEligibilityResponseWithVariousInputs:
    def test_not_actionable_and_check_response_when_rule_mapper_is_absent_but_rule_code_given(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_to_active_campaign_having_rules_with_rule_code_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "RSV",
                                    "status": "NotActionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "cohort_group1",
                                            "cohortStatus": "NotActionable",
                                            "cohortText": "positive_description",
                                        }
                                    ],
                                    "actions": [],
                                    "suitabilityRules": [
                                        {
                                            "ruleCode": "Rule Code Excluded age less than 75",
                                            "ruleText": "Exclude too young less than 75",
                                            "ruleType": "S",
                                        }
                                    ],
                                    "statusText": "You should have the RSV vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_not_actionable_and_check_response_when_rule_mapper_is_given(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_to_active_campaign_having_rules_with_rule_mapper_mapping: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "RSV",
                                    "status": "NotActionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "cohort_group1",
                                            "cohortStatus": "NotActionable",
                                            "cohortText": "positive_description",
                                        }
                                    ],
                                    "actions": [],
                                    "suitabilityRules": [
                                        {
                                            "ruleCode": "Age rule code from mapper",
                                            "ruleText": "Age Rule Description from mapper",
                                            "ruleType": "S",
                                        }
                                    ],
                                    "statusText": "You should have the RSV vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    @pytest.mark.parametrize(
        (
            "campaign_configs",
            "consumer_mappings",
            "consumer_id",
            "requested_conditions",
            "requested_category",
            "expected_targets",
        ),
        [
            # ============================================================
            # Group 1: Consumer is mapped, campaign exists in S3, requesting
            # ============================================================
            # 1.1 Consumer is mapped; multiple active campaigns exist; requesting ALL
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "consumer-id",
                "ALL",
                "VACCINATIONS",
                ["RSV", "COVID"],
            ),
            # 1.2 Consumer is mapped; requested single campaign exists and is mapped
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "consumer-id",
                "RSV",
                "VACCINATIONS",
                ["RSV"],
            ),
            # 1.3 Consumer is mapped; requested multiple campaigns exist and are mapped
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "consumer-id",
                "RSV,COVID",
                "VACCINATIONS",
                ["RSV", "COVID"],
            ),
            # ============================================================
            # Group 2: Consumer is mapped, campaign does NOT exist in S3
            # ============================================================
            # 2.1 Consumer is mapped; requested campaign exists in S3 but not mapped
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "consumer-id",
                "FLU",
                "VACCINATIONS",
                [],
            ),
            # 2.2 Consumer is mapped, but none of the mapped campaigns exist in S3
            (
                [
                    ("MMR", "MMR_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "consumer-id",
                "ALL",
                "VACCINATIONS",
                [],
            ),
            # 2.3 Consumer is mapped; requested mapped campaign does not exist in S3
            (
                [
                    ("MMR", "MMR_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "consumer-id",
                "RSV",
                "VACCINATIONS",
                [],
            ),
            # ============================================================
            # Group 3: Consumer is NOT mapped, campaign exists in S3
            # ============================================================
            # 3.1 Consumer not mapped; requesting ALL
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "another-consumer-id",
                "ALL",
                "VACCINATIONS",
                [],
            ),
            # 3.2 Consumer not mapped; requesting specific campaign
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "another-consumer-id",
                "RSV",
                "VACCINATIONS",
                [],
            ),
            # ============================================================
            # Group 4: Consumer NOT mapped, campaign does NOT exist in S3
            # ============================================================
            # 4.1 Consumer mapped; requested campaign does not exist
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {
                    "consumer-id": [
                        {"Campaign": "RSV_campaign_id"},
                        {"Campaign": "COVID_campaign_id"},
                    ]
                },
                "consumer-id",
                "HPV",
                "VACCINATIONS",
                [],
            ),
            # 4.2 No consumer mappings; requesting ALL
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {},
                "consumer-id",
                "ALL",
                "VACCINATIONS",
                [],
            ),
            # 4.3 No consumer mappings; requesting specific campaign
            (
                [
                    ("RSV", "RSV_campaign_id"),
                    ("COVID", "COVID_campaign_id"),
                    ("FLU", "FLU_campaign_id"),
                ],
                {},
                "consumer-id",
                "RSV",
                "VACCINATIONS",
                [],
            ),
        ],
        indirect=["campaign_configs", "consumer_mappings"],
    )
    def test_valid_response_when_consumer_has_a_valid_campaign_config_mapping(  # noqa: PLR0913
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        secretsmanager_client: BaseClient,  # noqa: ARG002
        campaign_configs: CampaignConfig,  # noqa: ARG002
        consumer_mappings: ConsumerMapping,  # noqa: ARG002
        consumer_id: str,
        requested_conditions: str,
        requested_category: str,
        expected_targets: list[str],
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        response = client.get(
            f"/patient-check/{persisted_person}?includeActions=Y&category={requested_category}&conditions={requested_conditions}",
            headers=headers,
        )

        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        # This ensures ONLY these items exist, no extras like FLU
                        contains_inanyorder(*[has_entry("condition", i) for i in expected_targets]),
                    )
                )
            ),
        )

    @pytest.mark.parametrize(
        ("consumer_id", "expected_campaign_id"),
        [
            # Consumer requesting for ALL
            # Consumer is mapped only to RSV_campaign_id_1
            ("consumer-id-1", "RSV_campaign_id_1"),
            # Consumer  is mapped only to RSV_campaign_id_2
            ("consumer-id-2", "RSV_campaign_id_2"),
            # Edge-case : Consumer-id-3a is mapped to multiple active campaigns, so only one taken.
            ("consumer-id-3a", "RSV_campaign_id_3"),
            # Edge-case : Consumer-id-3b is mapped to multiple active campaigns, so only one taken.
            ("consumer-id-3b", "RSV_campaign_id_3"),
            # Edge-case : Consumer is mapped to inactive inactive_RSV_campaign_id_5 and active RSV_campaign_id_6
            ("consumer-id-4", "RSV_campaign_id_6"),
            # Edge-case : Consumer is mapped only to inactive RSV_campaign_id_5
            ("consumer-id-5", None),
        ],
    )
    @pytest.mark.parametrize(
        ("campaign_configs", "consumer_mappings", "requested_conditions", "requested_category"),
        # consumer mappings and campaign configs are static here
        [
            (
                [
                    # Campaign configs in S3
                    ("RSV", "RSV_campaign_id_1"),
                    ("RSV", "RSV_campaign_id_2"),
                    ("RSV", "RSV_campaign_id_3"),
                    ("RSV", "RSV_campaign_id_4"),
                    ("RSV", "inactive_RSV_campaign_id_5", "inactive"),  # inactive iteration
                    ("RSV", "RSV_campaign_id_6"),
                ],
                {
                    # Consumer mappings in S3
                    "consumer-id-1": [{"Campaign": "RSV_campaign_id_1"}],
                    "consumer-id-2": [{"Campaign": "RSV_campaign_id_2"}],
                    "consumer-id-3a": [{"Campaign": "RSV_campaign_id_3"}, {"Campaign": "RSV_campaign_id_4"}],
                    "consumer-id-3b": [{"Campaign": "RSV_campaign_id_4"}, {"Campaign": "RSV_campaign_id_3"}],
                    "consumer-id-4": [{"Campaign": "inactive_RSV_campaign_id_5"}, {"Campaign": "RSV_campaign_id_6"}],
                    "consumer-id-5": [{"Campaign": "inactive_RSV_campaign_id_5"}],
                },
                "RSV",
                "VACCINATIONS",
            )
        ],
        indirect=["campaign_configs", "consumer_mappings"],
    )
    def test_if_correct_campaign_is_chosen_for_the_consumer_when_multiple_campaign_exists_per_target_giving_same_status(  # noqa : PLR0913
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        secretsmanager_client: BaseClient,  # noqa: ARG002
        audit_bucket: BucketName,
        s3_client: BaseClient,
        campaign_configs: CampaignConfig,  # noqa: ARG002
        consumer_mappings: ConsumerMapping,  # noqa: ARG002
        consumer_id: str,
        requested_conditions: str,
        requested_category: str,
        expected_campaign_id: list[str],
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), "consumer-id": consumer_id}

        # When
        client.get(
            f"/patient-check/{persisted_person}?includeActions=Y&category={requested_category}&conditions={requested_conditions}",
            headers=headers,
        )

        objects = s3_client.list_objects_v2(Bucket=audit_bucket).get("Contents", [])
        object_keys = [obj["Key"] for obj in objects]
        latest_key = sorted(object_keys)[-1]
        audit_data = json.loads(s3_client.get_object(Bucket=audit_bucket, Key=latest_key)["Body"].read())

        # Then
        if expected_campaign_id is not None:
            assert_that(len(audit_data["response"]["condition"]), equal_to(1))
            assert_that(audit_data["response"]["condition"][0].get("campaignId"), equal_to(expected_campaign_id))
        else:
            assert_that(len(audit_data["response"]["condition"]), equal_to(0))

    def test_if_campaign_having_best_status_is_chosen_if_there_exists_multiple_campaign_per_target(  # noqa : PLR0913
        self,
        client: FlaskClient,
        persisted_person_pc_sw19: NHSNumber,
        s3_client: BaseClient,
        consumer_mapping_bucket: BucketName,
        rules_bucket: BucketName,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        consumer_id = "consumer-n3bs-jo4hn-ce4na"
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19), "consumer-id": consumer_id}

        # Consumer Mapping Data
        s3_client.put_object(
            Bucket=consumer_mapping_bucket,
            Key="consumer_mapping.json",
            Body=json.dumps(
                {
                    consumer_id: [
                        {"Campaign": "RSV_campaign_id_not_actionable"},
                        {"Campaign": "RSV_campaign_id_actionable"},
                    ],
                }
            ),
            ContentType="application/json",
        )

        # Campaign configs
        campaign_1 = rule.CampaignConfigFactory.build(
            id="RSV_campaign_id_not_actionable",
            target="RSV",
            type="V",
            iterations=[
                rule.IterationFactory.build(
                    iteration_rules=[
                        rule.PostcodeSuppressionRuleFactory.build(name="Exclude SW19", description=""),
                    ],
                    iteration_cohorts=[
                        rule.IterationCohortFactory.build(
                            cohort_label="cohort1",
                            cohort_group="cohort_group1",
                            positive_description="positive_description",
                        )
                    ],
                    status_text=None,
                )
            ],
        )

        campaign_2 = rule.CampaignConfigFactory.build(
            id="RSV_campaign_id_actionable",
            target="RSV",
            type="V",
            iterations=[
                rule.IterationFactory.build(
                    iteration_rules=[
                        rule.PostcodeSuppressionRuleFactory.build(name="Exclude M4", comparator=RuleComparator("M4")),
                    ],
                    iteration_cohorts=[
                        rule.IterationCohortFactory.build(
                            cohort_label="cohort1",
                            cohort_group="cohort_group1",
                            positive_description="positive_description",
                        )
                    ],
                    status_text=None,
                )
            ],
        )

        for campaign in [campaign_1, campaign_2]:
            s3_client.put_object(
                Bucket=rules_bucket,
                Key=f"{campaign.id}.json",
                Body=json.dumps({"CampaignConfig": campaign.model_dump(by_alias=True)}),
                ContentType="application/json",
            )

        # When
        response = client.get(f"/patient-check/{persisted_person_pc_sw19}?includeActions=Y", headers=headers)

        # Then
        assert_that(
            response,
            is_response()
            .with_status_code(HTTPStatus.OK)
            .and_text(
                is_json_that(
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "RSV",
                                    "status": "Actionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "cohort_group1",
                                            "cohortStatus": "Actionable",
                                            "cohortText": "positive_description",
                                        }
                                    ],
                                    "actions": [
                                        {
                                            "actionCode": "action_code",
                                            "actionType": "defaultcomms",
                                            "description": "",
                                            "urlLabel": "",
                                            "urlLink": "",
                                        }
                                    ],
                                    "suitabilityRules": [],
                                    "statusText": "You should have the RSV vaccine",
                                }
                            ]
                        ),
                    )
                )
            ),
        )
