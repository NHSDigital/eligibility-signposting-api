import logging
import os

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
logger = logging.getLogger(__name__)


class DynamoDBHelper:
    def __init__(self, table_name):
        # Create DynamoDB resource using credentials from env
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def insert_item(self, item: dict):
        """
        Insert a single item into the table.
        """
        try:
            response = self.table.put_item(Item=item)
        except ClientError as e:
            logger.exception("Failed to insert item: %s", e.response["Error"]["Message"])
            raise
        else:
            return response

    def insert_items(self, items: list):
        """
        Insert multiple items using batch_writer.
        """
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
        except ClientError as e:
            logger.exception("Batch insert failed: %s", e.response["Error"]["Message"])
            raise
        else:
            logger.info("Batch insert complete.")

    def get_item(self, key: dict):
        """
        Retrieve a single item by primary key.
        """
        try:
            response = self.table.get_item(Key=key)
        except ClientError as e:
            logger.exception("Failed to get item: %s", e.response["Error"]["Message"])
            raise
        else:
            return response.get("Item")


def insert_into_dynamo(data):
    logger.info("Inserting into Dynamo: %s", data)
    table = DynamoDBHelper(os.getenv("DYNAMODB_TABLE_NAME"))
    for item in data:
        try:
            table.insert_item(item)
            logger.info("✅ Inserted: %s", item)
        except ClientError as e:
            logger.exception("❌ Failed to insert %s: %s", item, e.response["Error"]["Message"])
