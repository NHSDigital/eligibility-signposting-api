from http import HTTPStatus

from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask.testing import FlaskClient
from hamcrest import (
    assert_that,
    equal_to,
    has_entries,
    has_entry,
    has_key, contains_exactly,
)

from eligibility_signposting_api.model.campaign_config import CampaignConfig
from eligibility_signposting_api.model.eligibility_status import (
    NHSNumber,
)


class TestBaseLine:
    def test_nhs_number_given(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        campaign_config: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person)}

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
        campaign_config: CampaignConfig,  # noqa: ARG002
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
        campaign_config: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_no_cohorts)}

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
        campaign_config: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19)}

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

    def test_not_actionable(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        campaign_config: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person)}

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
        campaign_config: CampaignConfig,  # noqa: ARG002
    ):
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person)}

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
        campaign_config_with_and_rule: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person)}

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
        campaign_config_with_virtual_cohort: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19)}

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
        campaign_config_with_virtual_cohort: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person)}

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
        campaign_config_with_virtual_cohort: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person)}

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
        campaign_config_with_missing_descriptions_missing_rule_text: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_no_cohorts)}

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
        campaign_config_with_missing_descriptions_missing_rule_text: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person_pc_sw19)}

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
        campaign_config_with_missing_descriptions_missing_rule_text: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_person)}

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
        campaign_config_with_missing_descriptions_missing_rule_text: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person)}

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
        campaign_config_with_missing_descriptions_missing_rule_text: CampaignConfig,  # noqa: ARG002
    ):
        # Given
        headers = {"nhs-login-nhs-number": str(persisted_77yo_person)}

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
        assert_that(response, is_response()
                    .with_status_code(HTTPStatus.OK)
                    .and_json(has_entries({
            "status": "pass",
            "checks": has_entries({
                "healthcheckService:status": contains_exactly(
                    has_entries({
                        "status": "pass",
                        "timeout": False,
                        "responseCode": HTTPStatus.OK,
                        "outcome": "<html><h1>Ok</h1></html>",
                        "links": has_entries({
                            "self": "http://patient-check/_status"
                        })
                    })
                )
            })
        })))
