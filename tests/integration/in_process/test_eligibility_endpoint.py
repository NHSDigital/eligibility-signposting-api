from http import HTTPStatus

from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.werkzeug import is_werkzeug_response as is_response
from flask.testing import FlaskClient
from hamcrest import (
    assert_that,
    equal_to,
    has_entries,
    has_entry,
    has_key,
)

from eligibility_signposting_api.model.eligibility import (
    NHSNumber,
)
from eligibility_signposting_api.model.rules import CampaignConfig


class TestBaseLine:
    def test_nhs_number_given(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        campaign_config: CampaignConfig,  # noqa: ARG002
    ):
        # Given

        # When
        response = client.get(f"/patient-check/{persisted_person}")

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
            .with_status_code(HTTPStatus.NOT_FOUND)
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

        # When
        response = client.get(f"/patient-check/{persisted_person_no_cohorts}")

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
                                    "statusText": "Status.not_eligible",
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

        # When
        response = client.get(f"/patient-check/{persisted_person_pc_sw19}")

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
                                    "statusText": "Status.not_eligible",
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

        # When
        response = client.get(f"/patient-check/{persisted_person}")

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
                                    "statusText": "Status.not_actionable",
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
        # Given

        # When
        response = client.get(f"/patient-check/{persisted_77yo_person}")

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
                                    "actions": [{"action_type": "defaultcomms", "action_code": "action_code"}],
                                    "suitabilityRules": [],
                                    "statusText": "Status.actionable",
                                }
                            ]
                        ),
                    )
                )
            ),
        )


class TestMagicCohortResponse:
    def test_not_eligible_by_rule_when_only_magic_cohort_is_present(
        self,
        client: FlaskClient,
        persisted_person_pc_sw19: NHSNumber,
        campaign_config_with_magic_cohort: CampaignConfig,  # noqa: ARG002
    ):
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
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "COVID",
                                    "status": "NotEligible",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "magic cohort group",
                                            "cohortStatus": "NotEligible",
                                            "cohortText": "magic negative description",
                                        }
                                    ],
                                    "actions": [],
                                    "suitabilityRules": [],
                                    "statusText": "Status.not_eligible",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_not_actionable_when_only_magic_cohort_is_present(
        self,
        client: FlaskClient,
        persisted_person: NHSNumber,
        campaign_config_with_magic_cohort: CampaignConfig,  # noqa: ARG002
    ):
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
                    has_entry(
                        "processedSuggestions",
                        equal_to(
                            [
                                {
                                    "condition": "COVID",
                                    "status": "NotActionable",
                                    "eligibilityCohorts": [
                                        {
                                            "cohortCode": "magic cohort group",
                                            "cohortStatus": "NotActionable",
                                            "cohortText": "magic positive description",
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
                                    "statusText": "Status.not_actionable",
                                }
                            ]
                        ),
                    )
                )
            ),
        )

    def test_actionable_when_only_magic_cohort_is_present(
        self,
        client: FlaskClient,
        persisted_77yo_person: NHSNumber,
        campaign_config_with_magic_cohort: CampaignConfig,  # noqa: ARG002
    ):
        # Given

        # When
        response = client.get(f"/patient-check/{persisted_77yo_person}")

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
                                            "cohortCode": "magic cohort group",
                                            "cohortStatus": "Actionable",
                                            "cohortText": "magic positive description",
                                        }
                                    ],
                                    "actions": [{"action_type": "defaultcomms", "action_code": "action_code"}],
                                    "suitabilityRules": [],
                                    "statusText": "Status.actionable",
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

        # When
        response = client.get(f"/patient-check/{persisted_person_no_cohorts}")

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
                                    "statusText": "Status.not_eligible",
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

        # When
        response = client.get(f"/patient-check/{persisted_person_pc_sw19}")

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
                                    "statusText": "Status.not_eligible",
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

        # When
        response = client.get(f"/patient-check/{persisted_person}")

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
                                    "statusText": "Status.not_actionable",
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

        # When
        response = client.get(f"/patient-check/{persisted_77yo_person}")

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
                                    "actions": [{"action_code": "action_code", "action_type": "defaultcomms"}],
                                    "suitabilityRules": [],
                                    "statusText": "Status.actionable",
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

        # When
        response = client.get(f"/patient-check/{persisted_77yo_person}?includeActions=N")

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
                                    "statusText": "Status.actionable",
                                }
                            ]
                        ),
                    )
                )
            ),
        )
