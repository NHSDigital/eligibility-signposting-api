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

Before deploying this stack, you must manually create the required SSM parameters for Splunk integration:

#### 1. Create SSM Parameters Manually

```bash
# Create the HEC token parameter with your actual Splunk HEC token
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
# Plan the deployment to verify no changes to parameter values
make terraform env=<env> workspace=default stack=api-layer tf-command=plan

# Apply the changes
make terraform env=<env> workspace=default stack=api-layer tf-command=apply
```

## Environment Variables

The stack uses the following key variables:

- `environment`: Deployment environment (dev, staging, prod)
- `project_name`: Project identifier for resource naming
- `default_aws_region`: AWS region for resource deployment
