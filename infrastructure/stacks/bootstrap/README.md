# Provisioning a New AWS Account

Adapted from the [demographics serverless template](https://github.com/NHSDigital/demographics-serverless-template).

This guide explains how to initialize an AWS environment for use with Terraform. Specifically, it covers creating an S3 bucket for storing Terraform state (`.tfstate` file) and enabling state locking (`.tflock` file).

The Terraform code for this process is defined in the `bootstrap` module (`infrastructure/modules/bootstrap`) and invoked within the `bootstrap` stack (`infrastructure/stacks/bootstrap`).

This step should only need to be performed *once* per environment.

## Prerequisites

- **Terraform Installed**: Ensure Terraform is installed locally (see project prerequisites).
- **AWS Admin Role**: Access to an admin role for the AWS account where Terraform changes will be applied. You need to have
                      credentials set up to run this locally.
- **Environment-Specific Variables**: A `tfvars` file must exist for the environment in `infrastructure/stacks/_shared/tfvars`.

---

## 1. Running the Bootstrap Stack

### 1.1 Temporarily Disable the Backend Configuration

The bootstrap process creates the S3 bucket for storing Terraform state. Initially, we run the configuration without specifying an AWS backend (state is stored locally). Once the bucket is created, we enable the backend configuration to store state in S3.

Edit `infrastructure/stacks/bootstrap/state.tf` to comment out the backend block:

```hcl
terraform {
  required_version = ">= 1.11.1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.6, != 5.71.0"
    }
  }
  # backend "s3" {
  #   bucket = "eligibility-signposting-api-dev-tfstate"
  #   key    = "tfstate/terraform.tfstate"
  #   region = "eu-west-2"
  #   use_lockfile = true
  # }
}
```

### 1.2 Initialize Terraform and Plan

Run the following command to initialize Terraform and generate a plan. Replace `<env>` with the target environment:

```bash
make bootstrap-terraform env=<env> tf-command=plan
```

**Note**: If initialization fails, delete the following files and retry:

- `infrastructure/stacks/bootstrap/.terraform`
- `infrastructure/stacks/bootstrap/.terraform.lock.hcl`

### 1.3 Create a Workspace

Workspaces allow for alternative deployments within the same environment (e.g., testing changes in `dev`). Create a workspace with the same name as the environment:

```bash
make terraform-workspace env=<env> stack=bootstrap workspace=default
```

### 1.4 Apply Terraform Changes

Deploy the Terraform configuration using the following command:

```bash
make bootstrap-terraform env=<env> tf-command=apply args="-auto-approve=true"
```

---

## 2. Push Local State to the Remote S3 Bucket

### 2.1 Enable the Backend Configuration

Uncomment the backend block in `infrastructure/stacks/bootstrap/state.tf`:

```hcl
terraform {
  required_version = ">= 1.11.1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.6, != 5.71.0"
    }
  }
  backend "s3" {
    bucket = "eligibility-signposting-api-dev-tfstate"
    key    = "tfstate/terraform.tfstate"
    region = "eu-west-2"
    use_lockfile = true
  }
}
```

### 2.2 Reinitialize Terraform with the Backend

Reinitialize Terraform to migrate the state to the S3 bucket:

```bash
make terraform env=<env> workspace=default stack=bootstrap tf-command=apply
```

You will see a prompt like the following:

```bash
Do you want to migrate all workspaces to "s3"? [yes/no]
```

Type `yes` to push the local state to the remote S3 bucket.

---

## 3. Delete the Default VPC

The default VPC should be deleted from each region. This can be done via the AWS Console:

1. Navigate to the **VPC** service.
2. Select the default VPC (ensure the "Default" column is marked "yes").
3. Click **Actions** > **Delete VPC** and confirm the deletion.

---

## Notes

- Use `args=` to target specific modules during Terraform commands, e.g., `args="-target=module.tfstate -target=module.terraform_base_role"`.
- Always verify the environment and workspace before applying changes to avoid accidental modifications.
- If you want to test a new Terraform configuration in `dev`, set up a workspace linked to your branch/PR (e.g., `dev-PR123`), and then deploy according to the instructions.

---

This guide ensures a smooth setup of the Terraform backend and state management for new AWS accounts. Let us know if you encounter any issues!
