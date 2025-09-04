import argparse
import glob
import json
import logging
import os

import boto3

from token_value_mapper import token_to_value

logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Seed DynamoDB table with JSON data.")
    parser.add_argument("--table-name", required=True, help="Name of the DynamoDB table")
    parser.add_argument("--region", default="eu-west-2", help="AWS region")
    parser.add_argument("--data-folder", default="vitaIntegrationTestData/", help="Folder containing JSON seed data")
    return parser.parse_args()


def resolve_data_folder(path):
    return os.path.abspath(path)


def get_unique_nhs_numbers(data_folder):
    nhs_numbers = set()
    json_files = glob.glob(os.path.join(data_folder, "*.json"))
    for file_path in json_files:
        with open(file_path) as f:
            payload = json.load(f)
            items = payload.get("data", [])
            for item in items:
                nhs_number = item.get("NHS_NUMBER")
                if nhs_number:
                    nhs_numbers.add(nhs_number)
    return list(nhs_numbers)

def replace_tokens(item):
    for key, value in item.items():
        if isinstance(value, str) and value in token_to_value:
            item[key] = token_to_value[value]()
    return item

def delete_all_items_for_nhs_numbers(table, nhs_numbers):
    for nhs_number in nhs_numbers:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("NHS_NUMBER").eq(nhs_number)
        )
        items = response.get("Items", [])
        with table.batch_writer() as batch:
            for item in items:
                key = {
                    "NHS_NUMBER": item["NHS_NUMBER"],
                    "ATTRIBUTE_TYPE": item["ATTRIBUTE_TYPE"]
                }
                batch.delete_item(Key=key)


def insert_data_from_folder(table, data_folder):
    json_files = glob.glob(os.path.join(data_folder, "*.json"))
    for file_path in json_files:
        with open(file_path) as f:
            payload = json.load(f)
            items = payload.get("data", [])

        with table.batch_writer() as batch:
            for raw_item in items:
                item = replace_tokens(raw_item)
                nhs_number = item.get("NHS_NUMBER")
                attr_type = item.get("ATTRIBUTE_TYPE")
                if nhs_number and attr_type:
                    item["id"] = nhs_number
                    batch.put_item(Item=item)


def main():
    args = parse_args()

    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    table = dynamodb.Table(args.table_name)

    data_folder = resolve_data_folder(args.data_folder)
    if not os.path.isdir(data_folder):
        raise ValueError(f"Data folder '{data_folder}' does not exist or is not a directory.")

    nhs_numbers = get_unique_nhs_numbers(data_folder)
    delete_all_items_for_nhs_numbers(table, nhs_numbers)
    insert_data_from_folder(table, data_folder)
    logger.info("✅ Successfully inserted data from folder '%s' to table '%s'", data_folder, args.table_name)


if __name__ == "__main__":
    main()
