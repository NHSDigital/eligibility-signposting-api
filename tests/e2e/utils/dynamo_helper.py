import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load credentials from .env
load_dotenv()


class DynamoDBHelper:
    def __init__(self, table_name):
        # Create DynamoDB resource using credentials from env
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def insert_item(self, item: dict):
        """
        Insert a single item into the table.
        """
        try:
            response = self.table.put_item(Item=item)
            return response
        except ClientError as e:
            print(f"Failed to insert item: {e.response['Error']['Message']}")
            raise

    def insert_items(self, items: list):
        """
        Insert multiple items using batch_writer.
        """
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
            print("Batch insert complete.")
        except ClientError as e:
            print(f"Batch insert failed: {e.response['Error']['Message']}")
            raise

    def get_item(self, key: dict):
        """
        Retrieve a single item by primary key.
        """
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            print(f"Failed to get item: {e.response['Error']['Message']}")
            raise


def insert_into_dynamo(data):
    print("Inserting into Dynamo:", data)
    table = DynamoDBHelper("eligibility-signposting-api-test-eligibility_datastore")
    for item in data:
        try:
            table.insert_item(item)
            print(f"✅ Inserted: {item}")
        except ClientError as e:
            print(f"❌ Failed to insert {item}: {e.response['Error']['Message']}")
