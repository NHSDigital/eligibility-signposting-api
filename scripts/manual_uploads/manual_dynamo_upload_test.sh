#!/bin/bash
set -e

# Start LocalStack (assumes localstack is installed and in path)
echo "Starting LocalStack for DynamoDB..."
localstack start -d
sleep 5

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-2
export AWS_ENDPOINT_URL=http://localhost:4566

# Create DynamoDB table
aws --endpoint-url=$AWS_ENDPOINT_URL dynamodb create-table \
  --table-name test-table \
  --attribute-definitions AttributeName=UserId,AttributeType=S \
  --key-schema AttributeName=UserId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Create test item in DynamoDB JSON format
cat <<EOF > testitem.json
{
  "UserId": { "S": "123" },
  "Email": { "S": "localstack@test.com" },
  "Score": { "N": "100" }
}
EOF

# Run the script
echo "Testing manual_dynamo_upload.sh..."
./manual_dynamo_upload.sh testitem.json test-table

# Query item
echo "Querying DynamoDB table:"
aws --endpoint-url=$AWS_ENDPOINT_URL dynamodb get-item \
  --table-name test-table \
  --key '{ "UserId": { "S": "123" } }'

# Cleanup
rm testitem.json
localstack stop
