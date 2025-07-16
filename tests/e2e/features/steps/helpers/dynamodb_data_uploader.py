import json
import logging
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DynamoDBDataUploader:
    def __init__(self, aws_region, access_key, secret_key, session_token=None):
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=aws_region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
        )

    def upload_files_from_path(self, table_name: str, path: Path):
        if not path.exists() or not path.is_dir():
            logger.error("Seed path not found: %s", path)
            return 0

        table = self.dynamodb.Table(table_name)
        count = 0
        for file_path in path.glob("*.json"):
            try:
                with file_path.open() as f:
                    items = json.load(f)
                    if not isinstance(items, list):
                        logger.warning("Skipping non-list file: %s", file_path)
                        continue
                    for item in items:
                        table.put_item(Item=item)
                        count += 1
                    # logger.info("Inserted %d items from %s", len(items), file_path.name)
            except Exception:
                logger.exception("Failed to insert from file: %s", file_path)
        return count

    def delete_data(self):
        if not self.inserted_items:
            logger.info("No items were inserted — skipping cleanup.")
            return
        logger.info("Cleaning up seeded items from DynamoDB...")
        for item in self.inserted_items:
            nhs_number = item.get("NHS_NUMBER")
            attribute_type = item.get("ATTRIBUTE_TYPE")
            if nhs_number and attribute_type:
                try:
                    self.table.delete_item(Key={"NHS_NUMBER": nhs_number, "ATTRIBUTE_TYPE": attribute_type})
                    logger.info("Deleted item: %s - %s", nhs_number, attribute_type)
                except Exception:
                    logger.exception("Failed to delete item: %s - %s", nhs_number, attribute_type)
