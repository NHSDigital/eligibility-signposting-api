# ruff: noqa: INP001
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):  # noqa: ARG001,ANN201,ANN001
    logger.info("This is a log message from eligibility signposting api lambda function!")
    return {"statusCode": 200, "body": "Hello, World!"}
