from typing import Literal

URL_PREFIX = "patient-check"
RULE_STOP_DEFAULT = False
NHS_NUMBER_HEADER = "nhs-login-nhs-number"
CONSUMER_ID = "NHSE-Product-ID"
ALLOWED_CONDITIONS = Literal["COVID", "FLU", "MMR", "RSV"]
CONSUMER_MAPPING_FILE_NAME = "consumer_mapping_config.json"
