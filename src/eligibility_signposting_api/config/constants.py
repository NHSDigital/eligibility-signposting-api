from typing import Literal

URL_PREFIX = "patient-check"
RULE_STOP_DEFAULT = False
NHS_NUMBER_HEADER = "nhs-login-nhs-number"
CONSUMER_ID = "consumer-id"
ALLOWED_CONDITIONS = Literal["COVID", "FLU", "MMR", "RSV"]
