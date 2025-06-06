#!/bin/bash

# === Config ===
DEFAULT_TABLE="eligibility_data_store"
REGION="eu-west-2"
AWS_ENDPOINT_URL="${AWS_ENDPOINT_URL:-https://dynamodb.${REGION}.amazonaws.com}"

# === Usage Check ===

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <item.json> [table_name]"
  echo
  echo "Before running this, make sure AWS credentials are set either via:"
  echo "  • 'aws configure'"
  echo "  • OR by exporting:"
  echo "      export AWS_ACCESS_KEY_ID=..."
  echo "      export AWS_SECRET_ACCESS_KEY=..."
  echo "      export AWS_SESSION_TOKEN=..."
  exit 1
fi

FILE="$1"
TABLE="${2:-$DEFAULT_TABLE}"

# === Validate JSON ===

if ! jq empty "$FILE" >/dev/null 2>&1; then
  echo "Invalid JSON in file: $FILE"
  exit 1
fi

# === Prompt for AWS credentials if not set ===

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "AWS credentials not found. Let's set them now:"
  read -p "Enter AWS_ACCESS_KEY_ID: " AWS_ACCESS_KEY_ID
  read -s -p "Enter AWS_SECRET_ACCESS_KEY: " AWS_SECRET_ACCESS_KEY
  echo
  read -s -p "Enter AWS_SESSION_TOKEN (leave blank if not needed): " AWS_SESSION_TOKEN
  echo

  export AWS_ACCESS_KEY_ID
  export AWS_SECRET_ACCESS_KEY
  export AWS_SESSION_TOKEN
fi

# === Check AWS auth ===

aws sts get-caller-identity >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Failed to authenticate with AWS. Check credentials."
  exit 1
fi

# === Upload to DynamoDB ===

echo "Uploading item from $FILE to table $TABLE ..."
aws dynamodb put-item \
  --table-name "$TABLE" \
  --item "file://$FILE" \
  --region "$REGION" \
  --endpoint-url "$AWS_ENDPOINT_URL"

if [ $? -eq 0 ]; then
  echo "Upload complete."
else
  echo "Upload failed."
fi
