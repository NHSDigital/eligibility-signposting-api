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

from eligibility_signposting_api.config.constants import CONSUMER_ID
from eligibility_signposting_api.model.campaign_config import CampaignConfig
from eligibility_signposting_api.model.consumer_mapping import ConsumerId, ConsumerMapping
from eligibility_signposting_api.model.eligibility_status import (
    NHSNumber,
)


class TestBaseLine:
    def test_nhs_number_given(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        consumer_id: ConsumerId,
        consumer_mapping_with_rsv: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), CONSUMER_ID: consumer_id}

        # When
        response = client.get(f"/patient-check/{persisted_person}", headers=headers)

        # Then
        assert_that(
            response,
            is_response().with_status_code(HTTPStatus.OK).and_text(is_json_that(has_key("processedSuggestions"))),
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
        consumer_mapping_with_rsv: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_no_cohorts), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_rsv: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_rsv: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_rsv: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_campaign_config_with_and_rule: ConsumerMapping,  # noqa: ARG002
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_only_virtual_cohort: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_only_virtual_cohort: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_only_virtual_cohort: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_campaign_config_with_missing_descriptions_missing_rule_text: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_no_cohorts), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_campaign_config_with_missing_descriptions_missing_rule_text: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_campaign_config_with_missing_descriptions_missing_rule_text: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_campaign_config_with_missing_descriptions_missing_rule_text: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_campaign_config_with_missing_descriptions_missing_rule_text: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_campaign_config_with_rules_having_rule_code: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), CONSUMER_ID: consumer_id}

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
        consumer_mapping_with_campaign_config_with_rules_having_rule_mapper: ConsumerMapping,  # noqa: ARG002
        consumer_id: ConsumerId,
        secretsmanager_client: BaseClient,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person), CONSUMER_ID: consumer_id}

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
            # Scenario 1: Intersection of mapped targets, requested targets, and active campaigns (Success)
            (
                ["RSV", "COVID", "FLU"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
                "consumer-id",
                "ALL",
                "VACCINATIONS",
                ["RSV", "COVID"],
            ),
            # Scenario 2a: Explicit request for a single mapped target with an active campaign
            (
                ["RSV", "COVID", "FLU"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
                "consumer-id",
                "RSV",
                "VACCINATIONS",
                ["RSV"],
            ),
            # Scenario 2b: Explicit request for a single mapped target with an active campaign
            (
                ["RSV", "COVID", "FLU"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
                "consumer-id",
                "RSV,COVID",
                "VACCINATIONS",
                ["RSV", "COVID"],
            ),
            # Scenario 3: Request for an active campaign (FLU) that the consumer is NOT mapped to
            (
                ["RSV", "COVID", "FLU"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
                "consumer-id",
                "FLU",
                "VACCINATIONS",
                [],
            ),
            # Scenario 4: Request for a target that neither exists in system nor is mapped to consumer
            (
                ["RSV", "COVID", "FLU"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
                "consumer-id",
                "HPV",
                "VACCINATIONS",
                [],
            ),
            # Scenario 5: No mappings at all; requesting ALL should return empty
            (
                ["RSV", "COVID", "FLU"],
                {},
                "consumer-id",
                "ALL",
                "VACCINATIONS",
                [],
            ),
            # Scenario 6: No mappings at all; requesting RSV should return empty
            (
                ["RSV", "COVID", "FLU"],
                {},
                "consumer-id",
                "RSV",
                "VACCINATIONS",
                [],
            ),
            # Scenario 7: Consumer has no target mappings; requesting ALL should return empty
            (
                ["RSV", "COVID", "FLU"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
                "another-consumer-id",
                "ALL",
                "VACCINATIONS",
                [],
            ),
            # Scenario 8: Consumer has no target mappings; requesting specific target should return empty
            (
                ["RSV", "COVID", "FLU"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
                "another-consumer-id",
                "RSV",
                "VACCINATIONS",
                [],
            ),
            # Scenario 9: Consumer is mapped to targets (RSV/COVID), but those campaigns aren't active/present
            (
                ["MMR"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
                "consumer-id",
                "ALL",
                "VACCINATIONS",
                [],
            ),
            # Scenario 10: Request for specific mapped target (RSV), but those campaigns aren't active/present
            (
                ["MMR"],
                {"consumer-id": ["RSV_campaign_id", "COVID_campaign_id"]},
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
        headers = {"nhs-login-nhs-number": str(persisted_person), CONSUMER_ID: consumer_id}

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
