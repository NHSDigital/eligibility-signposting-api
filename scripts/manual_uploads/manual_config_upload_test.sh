#!/bin/bash
set -e

# Start LocalStack (assumes localstack is installed and in path)
echo "Starting LocalStack for S3..."
localstack start -d
sleep 5

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4566

# Create mock S3 bucket
aws --endpoint-url=$AWS_ENDPOINT_URL s3 mb s3://test-bucket

# Create test file
echo '{ "test": "value" }' > testfile.json

# Run the script
echo "Testing manual_config_upload.sh..."
./manual_config_upload.sh testfile.json test-bucket

# List contents
echo "Contents of bucket:"
aws --endpoint-url=$AWS_ENDPOINT_URL s3 ls s3://test-bucket/manual-uploads/

# Cleanup
rm testfile.json
localstack stop
