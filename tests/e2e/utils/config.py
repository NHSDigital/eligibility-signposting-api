"""Configuration module for the test framework."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
BASE_URL = os.getenv("BASE_URL", "https://sandbox.api.service.nhs.uk/eligibility-signposting-api")
API_KEY = os.getenv("API_KEY", "srgedsrgveg")

# Test Data
VALID_NHS_NUMBER = os.getenv("VALID_NHS_NUMBER", "50000000004")
INVALID_NHS_NUMBER = os.getenv("INVALID_NHS_NUMBER", "9876543210")

# API Endpoints
ELIGIBILITY_CHECK_ENDPOINT = "/eligibility-check"

# Response Schema
ELIGIBILITY_CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "responseId": {
            "type": "string",
            "description": "GUID assigned when the decisioning evaluation is carried out.",
        },
        "meta": {
            "type": "object",
            "properties": {
                "lastUpdated": {
                    "type": "string",
                    "description": "Timestamp of when the decisioning evaluation is carried out.",
                }
            },
        },
        "processedSuggestions": {
            "type": "array",
            "description": "List of suggestions the person is eligible for.",
            "items": {
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "string",
                        "description": "String representing the vaccine target disease, screening target or other scenario requiring decision based suggestions, that this suggestion relates to",
                    },
                    "status": {
                        "type": "string",
                        "description": "String representing an overall summary of the persons status for this processedSuggestion",
                        "enum": ["NotEligible", "NotActionable", "Actionable"],
                    },
                    "statusText": {"type": "string"},
                    "eligibilityCohorts": {
                        "type": "array",
                        "description": "Cohorts that drove the eligibility status returned.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "cohortCode": {
                                    "type": "string",
                                    "description": "Machine readable code signifying the cohort/cohort group that lead to a person's eligibility for this suggestion",
                                },
                                "cohortText": {
                                    "type": "string",
                                    "description": "Human readable (render-able) text describing the meaning of a cohort/cohort group that lead to a person's eligibility for this suggestion",
                                },
                                "cohortStatus": {
                                    "type": "string",
                                    "description": "String representing the persons status for this processedSuggestion in respect of this particular cohort or cohort group",
                                    "enum": ["NotEligible", "NotActionable", "Actionable"],
                                },
                            },
                        },
                    },
                    "suitablityRules": {
                        "type": "array",
                        "description": "Reasons that the eligibility status was changed from the base eligibility to result in it's status to not be eligible or to be acted on",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ruleType": {
                                    "type": "string",
                                    "description": "The type of a rule that triggered to amend the status of the suggestion",
                                    "enum": ["F", "S"],
                                },
                                "ruleCode": {
                                    "type": "string",
                                    "description": "Machine readable code signifying a rule that amended the status of the suggestion",
                                },
                                "ruleText": {
                                    "type": "string",
                                    "description": "Human readable (render-able) text describing a rule that amended the status of the suggestion",
                                },
                            },
                        },
                    },
                    "actions": {
                        "type": "array",
                        "description": "List of actions to be shown to the person.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "actionType": {
                                    "type": "string",
                                    "description": "Type of action to render.  E.g. A primary button, a link, text etc",
                                },
                                "actionCode": {
                                    "type": "string",
                                    "description": "Code representing the action to be taken",
                                },
                                "description": {"type": "string", "description": "A brief description of the step."},
                                "urlLink": {"type": "string", "description": "URL to invoke if action selected."},
                            },
                        },
                    },
                },
            },
        },
    },
}
