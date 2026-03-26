import boto3
import json
import pandas as pd
from datetime import datetime, timedelta

# --- Configuration ---
S3_BUCKET = "eligibility-signposting-api-dev-dq-metrics"
LOCAL_HYPER_PATH = "converted.hyper"
LOOKBACK_MONTHS = 3


def get_filtered_s3_data():
    s3 = boto3.client('s3')
    all_data = []

    # Calculate the date threshold (3 months ago)
    threshold_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
    print(f"Filtering for data where processing_date >= {threshold_date}...")

    # List objects in the bucket
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=S3_BUCKET):
        for obj in page.get('Contents', []):
            key = obj['Key']

            # Parse partition from Key (e.g. processing_date=20260303/datamart=cohorts/file.json)
            # We check if the key contains our date pattern
            try:
                if 'processing_date=' in key and key.endswith('.json'):
                    date_part = key.split('processing_date=')[1].split('/')[0]

                    if date_part >= threshold_date:
                        # Read JSON file
                        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                        line = response['Body'].read().decode('utf-8')

                        # Handle multiple JSON objects in one file (JSONL) if necessary
                        for json_line in line.strip().split('\n'):
                            if json_line:
                                all_data.append(json.loads(json_line))
            except Exception as e:
                print(f"Skipping key {key} due to error: {e}")

    return pd.DataFrame(all_data)


def create_hyper_from_df(df, hyper_path):
    from tableauhyperapi import (
        Connection, CreateMode, HyperProcess, Inserter,
        TableDefinition, Telemetry, SqlType, TableName, Date, Timestamp
    )

    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint, database=hyper_path,
                        create_mode=CreateMode.CREATE_AND_REPLACE) as connection:
            table_name = TableName("public", "Extract")

            # Define schema exactly as your Athena table
            schema = TableDefinition(table_name, [
                TableDefinition.Column("timestamp", SqlType.timestamp()),
                TableDefinition.Column("datamart", SqlType.text()),
                TableDefinition.Column("attribute_type", SqlType.text()),
                TableDefinition.Column("attribute", SqlType.text()),
                TableDefinition.Column("dimension", SqlType.text()),
                TableDefinition.Column("success_count", SqlType.big_int()),
                TableDefinition.Column("total_rows", SqlType.big_int()),
                TableDefinition.Column("success_percent", SqlType.double()),
                TableDefinition.Column("processing_date", SqlType.date()),
            ])

            connection.catalog.create_schema("Extract")
            connection.catalog.create_table(schema)

            with Inserter(connection, schema) as inserter:
                for _, row in df.iterrows():
                    # Parse timestamp string
                    ts = datetime.strptime(str(row['timestamp']), "%Y-%m-%d %H:%M:%S")
                    # Parse processing_date string (20260303)
                    pd_str = str(row['processing_date'])
                    pd_dt = datetime.strptime(pd_str, "%Y%m%d")

                    inserter.add_row([
                        Timestamp(ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second),
                        row.get('datamart'),
                        row.get('attribute_type'),
                        row.get('attribute', ''),
                        row.get('dimension'),
                        int(row.get('success_count', 0)),
                        int(row.get('total_rows', 0)),
                        float(row.get('success_percent', 0.0)),
                        Date(pd_dt.year, pd_dt.month, pd_dt.day)
                    ])
                inserter.execute()
    print(f"Hyper file created at {hyper_path}")


# --- Main Execution ---
df = get_filtered_s3_data()
if not df.empty:
    create_hyper_from_df(df, LOCAL_HYPER_PATH)
else:
    print("No data found for the selected date range.")
