#!/bin/bash

# === Config ===

BUCKET_NAME="eligibility-signposting-api-dev-eli-rules"
S3_PREFIX="manual-uploads"

# === Usage Info ===
# make it executable using - chmod +x manual_config_upload.sh

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <file.json> [bucket_name]"
  echo
  echo "Before running this script, you should either:"
  echo "  • Run 'aws configure'"
  echo "  • OR export these variables:"
  echo "      export AWS_ACCESS_KEY_ID=..."
  echo "      export AWS_SECRET_ACCESS_KEY=..."
  echo "      export AWS_SESSION_TOKEN=...  # if using temporary credentials"
  echo
  exit 1
fi
FILE="$1"
BUCKET="${2:-$BUCKET_NAME}"

# === Check dependencies ===

if ! command -v jq >/dev/null 2>&1; then
  echo " 'jq' is not installed. Please install it (e.g., sudo apt install jq)"
  exit 1
fi

# === Validate JSON ===

if ! jq empty "$FILE" >/dev/null 2>&1; then
  echo " Invalid JSON in file: $FILE"
  exit 1
fi

# === Prompt for AWS credentials if not set ===

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "AWS credentials not found in environment. Let's set them now:"
  read -p "Enter AWS_ACCESS_KEY_ID: " AWS_ACCESS_KEY_ID
  read -s -p "Enter AWS_SECRET_ACCESS_KEY: " AWS_SECRET_ACCESS_KEY
  echo
  read -s -p "Enter AWS_SESSION_TOKEN (leave blank if not needed): " AWS_SESSION_TOKEN
  echo  export AWS_ACCESS_KEY_ID
  export AWS_SECRET_ACCESS_KEY
  export AWS_SESSION_TOKEN
fi

# === Confirm credentials work ===

aws sts get-caller-identity >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Failed to authenticate with AWS. Please check your credentials."
  exit 1

fi

# === Create unique key ===

BASENAME=$(basename "$FILE" .json)
S3_KEY="${S3_PREFIX}/${BASENAME}.json"

# === Upload ===

echo " JSON is valid. Uploading to s3://$BUCKET/$S3_KEY ..."
aws s3 cp "$FILE" "s3://$BUCKET/$S3_KEY" --content-type "application/json"

if [ $? -eq 0 ]; then
  echo " Upload complete."
else
  echo "Upload failed."
fi
