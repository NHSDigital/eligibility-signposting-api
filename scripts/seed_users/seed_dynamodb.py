import argparse
import glob
import json
import os

import boto3


def parse_args():
    parser = argparse.ArgumentParser(description="Seed DynamoDB table with JSON data.")
    parser.add_argument("--table-name", required=True, help="Name of the DynamoDB table")
    parser.add_argument("--region", default="eu-west-2", help="AWS region")
    parser.add_argument("--data-folder", default="vitaIntegrationTestData/", help="Folder containing JSON seed data")
    return parser.parse_args()


def get_keys_from_folder(data_folder):
    keys_to_delete = []
    json_files = glob.glob(os.path.join(data_folder, "*.json"))
    for file_path in json_files:
        with open(file_path) as f:
            payload = json.load(f)
            items = payload.get("data", [])
            for item in items:
                nhs_number = item.get("NHS_NUMBER")
                attr_type = item.get("ATTRIBUTE_TYPE")
                if nhs_number and attr_type:
                    keys_to_delete.append({"NHS_NUMBER": nhs_number, "ATTRIBUTE_TYPE": attr_type})
    return keys_to_delete


def delete_specific_items(table, keys):
    with table.batch_writer() as batch:
        for key in keys:
            batch.delete_item(Key=key)


def insert_data_from_folder(table, data_folder):
    json_files = glob.glob(os.path.join(data_folder, "*.json"))
    for file_path in json_files:
        with open(file_path) as f:
            payload = json.load(f)
            items = payload.get("data", [])

        with table.batch_writer() as batch:
            for item in items:
                nhs_number = item.get("NHS_NUMBER")
                attr_type = item.get("ATTRIBUTE_TYPE")
                if nhs_number and attr_type:
                    item["id"] = nhs_number
                    batch.put_item(Item=item)


def main():
    args = parse_args()
    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    table = dynamodb.Table(args.table_name)

    keys_to_delete = get_keys_from_folder(args.data_folder)
    delete_specific_items(table, keys_to_delete)
    insert_data_from_folder(table, args.data_folder)


if __name__ == "__main__":
    main()
