# IAMS Development Roles

## Purpose

The IAMS Roles stack creates a dedicated IAM role that allows authorized developers to securely plan and apply Terraform infrastructure changes. This role follows the principle of least privilege by granting only the permissions necessary for managing infrastructure resources via Terraform.

## Resources Created

This stack creates the following AWS resources:

- An IAM role (`terraform-developer-role`) that can be assumed by authorized AWS SSO users
- An IAM policy that grants permissions to manage infrastructure resources
- Trust relationships that control who can assume the role

## Deployment Instructions

### Prerequisites

- AWS CLI configured with credentials that have permissions to create IAM roles
- Terraform v1.11.1 or higher
- Access to an AWS account with SSO configuration

### Deployment Steps

1. **Set up your environment variables**:

   ```bash
   export TF_VAR_environment=dev  # or test, prod as appropriate
   ```

2. Initialize the Terraform configuration:

    ```bash
    make terraform-init env=dev stack=iams-developer-roles
    ```

3. Plan the deployment:

    ```bash
    make terraform env=dev stack=iams-developer-roles tf-command=plan workspace=default
    ```

4. Apply the configuration:

    ```bash
    make terraform env=dev stack=iams-developer-roles tf-command=apply workspace=default
    ```

5. Verify the role was created:

    ```bash
    aws iam get-role --role-name terraform-developer-role
    ```

## Using the Role

Once the role is deployed, authorized developers can assume this role to make infrastructure changes:

```bash
aws sts assume-role --role-arn arn:aws:iam::<ACCOUNT_ID>:role/terraform-developer-role --role-session-name TerraformSession
```

For Terraform commands:

```bash
# Set environment variables with the assumed role credentials
export AWS_ACCESS_KEY_ID=<from-assume-role-response>
export AWS_SECRET_ACCESS_KEY=<from-assume-role-response>
export AWS_SESSION_TOKEN=<from-assume-role-response>

# Run Terraform commands
make terraform env=dev stack=<stack of choice> tf-command=plan workspace=dev
```
