import json
from pathlib import Path

from pydantic import ValidationError

from rules_validation_api.validators.campaign_config_validator import CampaignConfigValidation


def main() -> None:
    with Path.open(Path("campaign_config.json")) as file:
        json_data = json.load(file)  # this validates json

    try:
        CampaignConfigValidation(**json_data["CampaignConfig"])
    except ValidationError as e:
        print(e)  # noqa: T201


if __name__ == "__main__":
    main()
