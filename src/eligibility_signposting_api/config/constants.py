from typing import Literal

URL_PREFIX = "patient-check"
RULE_STOP_DEFAULT = False
NHS_NUMBER_HEADER = "nhs-login-nhs-number"
CONSUMER_ID = "NHSE-Product-ID"
ALLOWED_CONDITIONS = Literal["COVID", "FLU", "MMR", "RSV"]
CONSUMER_MAPPING_FILE_NAME = "consumer_mapping_config.json"
RESERVED_TEST_CONSUMER_IDS = {"test-consumer-1", "test-consumer-2", "test-consumer-3"}

TTL = {
    "test": 300,
    "dev": 300,
    "preprod": 300,
    "prod": 300,
}
