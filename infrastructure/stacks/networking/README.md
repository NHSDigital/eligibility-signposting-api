# Networking stack

The networking stack contains the networking resources that are securing the Eligibility Signposting API application resources.

The stack is documented on [this Confluence page](https://nhsd-confluence.digital.nhs.uk/spaces/Vacc/pages/1054575846/VPC+structure)

## Traffic Flow Explanation

### Public HTTPS Request Flow

* External client makes HTTPS request → Internet Gateway
* Request routes to Load Balancer or API Gateway in public subnet
* Request forwards to Lambda (or other application) in private subnet
* Lambda processes the request and returns response
* Response returns to client through the same path

### Outbound Internet Access

* Lambda functions in private subnets can make outbound internet calls via NAT Gateways
* This allows Lambda to call external APIs, download packages, etc.
* No direct inbound access to Lambda from the internet

### Internal-Only Traffic

* Lambda functions access AWS services via VPC Endpoints:
  * Gateway Endpoints: S3, DynamoDB
  * Interface Endpoints: KMS, CloudWatch, SSM, Secrets Manager, Lambda, STS, SQS
* All traffic between Lambda and AWS services stays within the AWS network
* No internet transit required for AWS service access

### Security Controls

#### Network ACLs

Public subnets: Allow HTTP(80), HTTPS(443), ephemeral ports
Private subnets: Allow VPC traffic and responses to outbound requests

#### Security Groups

Default security group: Deny all
VPC Endpoint security group: Allow HTTPS(443) from within VPC

#### Route Tables

Public subnets: Route to Internet Gateway for external access
Private subnets: Route to NAT Gateways for outbound-only access

## Deployment to AWS Development Environment

This stack should only ever be deployed once per account (e.g. the use of Terraform workspaces is explicitly not recommended beyond specifying `dev` as the environment).

Deployment to the Development environment is done through use of `make` commands

### Initialize Terraform and Plan

Run the following command to initialize Terraform and generate a plan. Replace `<env>` with the target environment:

```bash
make terraform env=dev stack=networking tf-command=init workspace=<env>
```

then

```bash
make terraform env=dev stack=networking tf-command=plan workspace=<env>
```

### 1.4 Apply Terraform Changes

Deploy the Terraform configuration using the following command:

```bash
make terraform env=dev stack=networking tf-command=apply workspace=<env>
```

## Release Deployment to AWS (Int, Ref and Prod)

Deployment to Int, Ref and Prod, as well as running the automated tests can be done via GitHub actions, when they are developed.
