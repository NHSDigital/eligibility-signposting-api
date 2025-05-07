# ruff: noqa: INP001
from mangum.types import LambdaContext, LambdaEvent


def lambda_handler(event: LambdaEvent, context: LambdaContext):  # noqa: ARG001,ANN201
    return {"statusCode": 200, "body": "Hello, World!"}
