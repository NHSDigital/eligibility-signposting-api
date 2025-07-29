import json

from pydantic import ValidationError

from rules_validation_api.validators.campaign_config_validator import CampaignConfigValidation


def main() -> None:
    print("Starting rules validation")
    with open('campaign_config.json', 'r') as file:
        json_data = json.load(file) # this validates json

    try:
        user = CampaignConfigValidation(**json_data["CampaignConfig"])
        print("validation successful")
    except ValidationError as e:
        print(e)



if __name__ == "__main__":
    main()
