from typing import Literal

URL_PREFIX = "patient-check"
RULE_STOP_DEFAULT = False
NHS_NUMBER_HEADER = "nhs-login-nhs-number"
ALLOWED_CONDITIONS = Literal["COVID", "FLU", "MMR", "RSV"]
