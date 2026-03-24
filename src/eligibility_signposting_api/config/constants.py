from typing import Literal
import os

URL_PREFIX = "patient-check"
RULE_STOP_DEFAULT = False
NHS_NUMBER_HEADER = "nhs-login-nhs-number"
CONSUMER_ID = "NHSE-Product-ID"
ALLOWED_CONDITIONS = Literal["COVID", "FLU", "MMR", "RSV"]
CONSUMER_MAPPING_FILE_NAME = "consumer_mapping_config.json"
RESERVED_TEST_CONSUMER_IDS = {"test-consumer-1", "test-consumer-2", "test-consumer-3"}

CACHE_TTL_SECONDS = int(os.getenv("CONFIG_CACHE_TTL_SECONDS", "1800"))
