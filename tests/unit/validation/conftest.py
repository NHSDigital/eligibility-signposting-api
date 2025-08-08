import pytest


@pytest.fixture
def valid_campaign_config_with_only_mandatory_fields():
    return {
        "ID": "CAMP001",
        "Version": 1,
        "Name": "Spring Campaign",
        "Type": "V",
        "Target": "COVID",
        "IterationFrequency": "M",
        "IterationType": "A",
        "StartDate": "20250101",
        "EndDate": "20250331",
        "Iterations": [
            {
                "ID": "ITER001",
                "Version": 1,
                "Name": "Mid-January Push",
                "IterationDate": "20250101",
                "IterationNumber": 1,
                "ApprovalMinimum": 10,
                "ApprovalMaximum": 100,
                "Type": "A",
                "DefaultCommsRouting": "",
                "DefaultNotEligibleRouting": "",
                "DefaultNotActionableRouting": "",
                "IterationCohorts": [],
                "IterationRules": [],
                "ActionsMapper": {},
            }
        ],
    }


@pytest.fixture
def valid_iteration_rule_with_only_mandatory_fields():
    return {
        "Type": "F",
        "Name": "Assure only already vaccinated taken from magic cohort",
        "Description": "Exclude anyone who has NOT been given a dose of RSV Vaccination from the magic cohort",
        "Operator": "is_empty",
        "Comparator": "",
        "AttributeTarget": "RSV",
        "AttributeLevel": "TARGET",
        "AttributeName": "LAST_SUCCESSFUL_DATE",
        "CohortLabel": "elid_all_people",
        "Priority": 100,
    }


@pytest.fixture
def valid_available_action():
    return {
        "ExternalRoutingCode": "BookNBS",
        "ActionDescription": "",
        "ActionType": "ButtonWithAuthLink",
        "UrlLink": "http://www.nhs.uk/book-rsv",
        "UrlLabel": "Continue to booking",
    }
