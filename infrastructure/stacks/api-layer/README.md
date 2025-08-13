# API Layer Stack

## Overview

The API Layer stack is the core infrastructure stack that provisions the main application components for the Eligibility Signposting API. This stack creates and manages the runtime environment, data storage, monitoring, and logging infrastructure required for the application to operate.

## Components

### Core Infrastructure

- **Lambda Functions**: Serverless compute for the eligibility signposting API
- **DynamoDB Table**: Primary data store for eligibility status information
- **S3 Buckets**: Storage for rules, audit data, truststore, and backup files
- **API Gateway**: HTTP API endpoint for external access
- **VPC Configuration**: Networking and security groups for isolated execution

### Data & Storage

- **DynamoDB**: Encrypted table with KMS key for eligibility data storage
- **S3 Buckets**:
  - Rules bucket for configuration data
  - Audit bucket for compliance logging
  - Truststore bucket for certificates
  - Firehose backup bucket for failed log delivery

### Monitoring & Logging

- **CloudWatch Alarms**: Monitoring for application health and performance
- **Kinesis Firehose**: Log streaming to Splunk for centralized monitoring
- **EventBridge**: Alarm forwarding to external monitoring systems
- **X-Ray Tracing**: Distributed tracing for request tracking

### Security

- **KMS Keys**: Encryption for DynamoDB, S3, SNS, and SSM parameters
- **IAM Roles**: Service-specific roles with least privilege access
- **Permissions Boundaries**: Additional security controls for assumed roles
- **SSM Parameters**: Secure storage for sensitive configuration

## Dependencies

This stack depends on:

- **Bootstrap Stack**: Terraform state storage and base infrastructure
- **Networking Stack**: VPC, subnets, and security groups
- **IAMS Developer Roles Stack**: GitHub Actions deployment role

## Pre-Deployment Requirements

### Splunk Integration Setup

Before deploying this stack, you must manually create the required SSM parameters for Splunk integration. Create them initially with AWS managed encryption, then Terraform will automatically migrate them to use the customer-managed KMS key during deployment.

#### 1. Create SSM Parameters Manually

```bash
# Create the HEC token parameter with your actual Splunk HEC token
# Use AWS managed encryption initially since customer KMS key doesn't exist yet
aws ssm put-parameter \
  --name "/splunk/hec/token" \
  --value "YOUR_ACTUAL_HEC_TOKEN" \
  --type "SecureString" \
  --tier "Advanced" \
  --description "Splunk HEC token"

# Create the HEC endpoint parameter with your actual Splunk endpoint
aws ssm put-parameter \
  --name "/splunk/hec/endpoint" \
  --value "https://your-splunk-instance.com:8088/services/collector/event" \
  --type "SecureString" \
  --tier "Advanced" \
  --description "Splunk HEC endpoint"
```

#### 2. Import Parameters into Terraform State

```bash
# Navigate to the api-layer stack directory
cd infrastructure/stacks/api-layer

# Import the existing parameters into Terraform state
terraform import aws_ssm_parameter.splunk_hec_token "/splunk/hec/token"
terraform import aws_ssm_parameter.splunk_hec_endpoint "/splunk/hec/endpoint"
```

#### 3. Deploy the Stack

```bash
# Plan the deployment - this will show the KMS key migration
terraform plan

# Apply the changes - this will create the KMS key and migrate the SSM parameters
terraform apply
```

**Note**: During the `terraform apply`, the SSM parameters will be automatically updated to use the customer-managed KMS key while preserving their values.

### Getting Splunk HEC Credentials

To obtain the required Splunk HEC token and endpoint:

1. **Access Splunk Instance**: Log into your Splunk deployment
2. **Navigate to Data Inputs**: Go to Settings > Data Inputs > HTTP Event Collector
3. **Create/Configure HEC Token**:
   - Create a new token or use an existing one
   - Ensure the token is enabled and has appropriate permissions
   - Note the token value for the SSM parameter
4. **Get HEC Endpoint**: The endpoint typically follows the format:
   - `https://your-splunk-instance.com:8088/services/collector/event`
   - Replace with your actual Splunk instance URL and port

## Environment Variables

The stack uses the following key variables:

- `environment`: Deployment environment ("dev", "test", "preprod", "prod")
- `project_name`: Project identifier for resource naming
- `default_aws_region`: AWS region for resource deployment
