# Networking Stack

This stack provisions the networking resources that secure the Eligibility Signposting API application.

For a high-level overview, see the [VPC Structure Confluence Page](https://nhsd-confluence.digital.nhs.uk/spaces/Vacc/pages/1054575846/VPC+structure).

---

## Table of Contents

- [Networking Stack](#networking-stack)
  - [Table of Contents](#table-of-contents)
  - [Traffic Flow Explanation](#traffic-flow-explanation)
    - [Public HTTPS Request Flow](#public-https-request-flow)
    - [Outbound Internet Access](#outbound-internet-access)
    - [Internal-Only Traffic](#internal-only-traffic)
  - [Security Controls](#security-controls)
    - [Network ACLs](#network-acls)
    - [Security Groups](#security-groups)
    - [Route Tables](#route-tables)
  - [Deployment to AWS Development Environment](#deployment-to-aws-development-environment)
    - [1. Initialize Terraform and Plan](#1-initialize-terraform-and-plan)
    - [2. Apply Terraform Changes](#2-apply-terraform-changes)
  - [Release Deployment to AWS (Int, Ref, and Prod)](#release-deployment-to-aws-int-ref-and-prod)
  - [ACM Certificates Needed for Each Environment](#acm-certificates-needed-for-each-environment)
    - [Domain Validation](#domain-validation)
      - [Steps](#steps)
    - [mTLS Certificates](#mtls-certificates)
      - [1. Generate a CSR](#1-generate-a-csr)
      - [2. Send the CSR for Signing](#2-send-the-csr-for-signing)
      - [3. Add Root and Intermediate CAs to Truststore](#3-add-root-and-intermediate-cas-to-truststore)
      - [4. Validate the CSR](#4-validate-the-csr)
      - [5. Upload the CSR and Keys to SSM](#5-upload-the-csr-and-keys-to-ssm)
      - [6. Upload the mTLS Secrets to Proxygen](#6-upload-the-mtls-secrets-to-proxygen)
  - [Additional Resources](#additional-resources)

---

## Traffic Flow Explanation

### Public HTTPS Request Flow

1. External client makes HTTPS request to API Gateway
2. Request forwards to Lambda (or other application) in private subnet
3. Lambda processes the request and returns response
4. Response returns to client through the same path

### Outbound Internet Access

- No direct inbound or outbound access to Lambda from the internet

### Internal-Only Traffic

- Lambda functions access AWS services via VPC Endpoints:
  - **Gateway Endpoints:** S3, DynamoDB
  - **Interface Endpoints:** KMS, CloudWatch, SSM, Secrets Manager, Lambda, STS, SQS
- All traffic between Lambda and AWS services stays within the AWS network

---

## Security Controls

### Network ACLs

- **Private subnets:** Allow VPC traffic and responses to outbound requests

### Security Groups

- **Default security group:** Deny all
- **VPC Endpoint security group:** Allow HTTPS (443) from within VPC

### Route Tables

- **Private subnets:** Route to VPC Endpoints only

---

## Deployment to AWS Development Environment

> **Note:** This stack should only be deployed once per account. Use of Terraform workspaces is not recommended beyond specifying `dev` as the environment.

### 1. Initialize Terraform and Plan

Run the following command to initialize Terraform and generate a plan. Replace `<env>` with your target environment (e.g., `dev`):

```bash
make terraform env=dev stack=networking tf-command=init workspace=default
make terraform env=dev stack=networking tf-command=plan workspace=default
```

### 2. Apply Terraform Changes

Deploy the Terraform configuration:

```bash
make terraform env=dev stack=networking tf-command=apply workspace=default
```

For more on Terraform, see the [Terraform Documentation](https://developer.hashicorp.com/terraform/docs).

---

## Release Deployment to AWS (Int, Ref, and Prod)

Deployment to Int, Ref, and Prod, as well as running automated tests, can be done via GitHub Actions (when implemented).

---

## ACM Certificates Needed for Each Environment

To verify domain ownership and enable secure communication with the APIM API Proxy, you need:

1. **A domain validation certificate**
2. **mTLS certificates and secrets**

> **Manual intervention is required for creation of these assets.**

---

### Domain Validation

The ACM Certificate Manager is used to request a domain validation certificate (see `infrastructure/stacks/networking/acm_certificates.tf`).
Running Terraform will create this certificate, but DNS validation requires action from the DNS Team.

#### Steps

1. In the AWS Console, navigate to **Certificate Manager** for the environment account.
2. In **Domains**, download the CSV of the CNAME details.
3. Email `england.dnsteam@nhs.net` with the subject:
   `eligibility-signposting-api.nhs.uk - Requesting a sub domain - <env>`
   Attach the exported CSV and use the following template:

   ```text
   Hi DNS Team,

   Please could we add the subdomain '<env>' for our top level domain 'eligibility-signposting-api.nhs.uk'?

   e.g.

   <env>.eligibility-signposting-api.nhs.uk

   We've generated an ACM certificate for DNS validation, which has generated a CNAME name and value which I think would need adding to your records to allow us to validate. I've attached this to the email in a CSV, please let us know if this isn't the approach you expect.

   Thanks,

   Edd
   ```

4. Check the certificate for DNS validation once you receive confirmation that the subdomain was created.

- [AWS ACM DNS Validation Guide](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)

---

### mTLS Certificates

See the [APIM documentation](https://nhsd-confluence.digital.nhs.uk/spaces/APM/pages/734397569/How+to+implement+mutual+TLS+mTLS+security+for+your+API+backend) for more details.

#### 1. Generate a CSR

1. Create a configuration file for the environment, e.g., `dev.conf`:

   ```ini
   [req]
   default_bits = 4096
   distinguished_name = req_distinguished_name
   req_extensions = v3_req
   prompt = no

   [req_distinguished_name]
   C = GB
   ST = West Yorkshire
   L = Leeds
   O = NHS England
   OU = API Management
   CN = dev.eligibility-signposting-api.nhs.uk

   [v3_req]
   keyUsage = keyEncipherment, dataEncipherment
   extendedKeyUsage = serverAuth
   ```

2. Generate the CSR and private key:

   ```bash
   mkdir -p csrs keys
   openssl req -new -newkey rsa:4096 -nodes -sha256 \
     -keyout keys/<env>.eligibility-signposting-api.nhs.uk.key \
     -out csrs/<env>.eligibility-signposting-api.nhs.uk.csr \
     -config <env>.conf -extensions v3_req
   ```

   - [OpenSSL CSR Generation Guide](https://www.openssl.org/docs/manmaster/man1/openssl-req.html)

#### 2. Send the CSR for Signing

- **Non-production environments:**
  Email `itoc.supportdesk@nhs.net` and reference the INT / PTL environment.
- **Production environments:**
  Email `dir@nhs.net`.

Template:

```text
Hi,

Please could I get the attached CSR signed. Details as follows:

Name:
Company/Organisation: Eligibility Data Team, NHS England
Contact Number:
Common Name (CN):  dev.eligibility-signposting-api.nhs.uk
Reason for the Certificate: New APIM client
Environment: INT / PTL

Thanks,

Edd
```

#### 3. Add Root and Intermediate CAs to Truststore

1. Download the INT CA certificates from [NHS Digital G2 Certificate Technical Implementation](https://digital.nhs.uk/services/spine/updating-nhs-public-key-infrastructure-certificates/g2-certificate-technical-implementation#certificate-downloads).
2. Concatenate the certificates (order matters):

   ```bash
   cat intermediate-cert.pem root-cert.pem > truststore.pem
   ```

   This file is used in `infrastructure/stacks/api-layer/truststore_s3_bucket.tf`.

3. Upload `truststore.pem` to the specified S3 bucket.

#### 4. Validate the CSR

```bash
openssl verify -CAfile truststore.pem new-cert.crt
```

You should see an `OK` response.

#### 5. Upload the CSR and Keys to SSM

Store the following in AWS SSM Parameter Store (see `infrastructure/stacks/networking/ssm.tf`):

- `/${var.environment}/mtls/api_ca_cert` — the combined CA cert (`truststore.pem`)
- `/${var.environment}/mtls/api_client_cert` — the signed client certificate
- `/${var.environment}/mtls/api_private_key_cert` — the private key

- [AWS SSM Parameter Store Documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)

#### 6. Upload the mTLS Secrets to Proxygen

Requires the [Proxygen CLI](https://github.com/NHSDigital/proxygen-cli). The [specification repository](https://github.com/NHSDigital/eligibility-signposting-api-specification)
includes the CLI, and includes details of how to set up authentication with Proxygen.

After logging into AWS for the appropriate environment, run:

```bash
mkdir -p ~/.proxygen
aws ssm get-parameter --name /$AWS_ENV/mtls/api_client_cert --with-decryption | jq ".Parameter.Value" --raw-output > ~/.proxygen/client_cert.pem
aws ssm get-parameter --name /$AWS_ENV/mtls/api_private_key_cert --with-decryption | jq ".Parameter.Value" --raw-output > ~/.proxygen/private_key.pem
proxygen secret put --mtls-cert ~/.proxygen/client_cert.pem --mtls-key ~/.proxygen/private_key.pem $APIM_ENV $secret_name
rm ~/.proxygen/client_cert.pem ~/.proxygen/private_key.pem
```

---

## Additional Resources

- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [AWS ACM Documentation](https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html)
- [AWS SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [Proxygen CLI](https://github.com/NHSDigital/proxygen-cli)

---

*For any issues or questions, please contact the Eligibility Data Team.*
