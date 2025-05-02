locals {
  # tflint-ignore: terraform_unused_declarations
  environment = var.environment
  # tflint-ignore: terraform_unused_declarations
  workspace = lower(terraform.workspace)
  # tflint-ignore: terraform_unused_declarations
  runtime = "python3.13.1"

  # tflint-ignore: terraform_unused_declarations
  tags = {
    TagVersion      = "1"
    Programme       = "Vaccinations"
    Project         = "EligibilitySignpostingAPI"
    Environment     = var.environment
    ServiceCategory = var.environment == "prod" ? "Bronze" : "N/A"
    Tool            = "Terraform"
    workspace       = lower(terraform.workspace)
  }

  sso_role_patterns = {
    dev  = "AWSReservedSSO_vdselid_dev_*"
    test = "AWSReservedSSO_vdselid_test_*"
    preprod = "AWSReservedSSO_vdselid_preprod_*"
  }

  terraform_state_bucket_name = "eligibility-signposting-api-${var.environment}-tfstate"
  terraform_state_bucket_arn = "arn:aws:s3:::eligibility-signposting-api-${var.environment}-tfstate"

  account_ids = {
    dev     = "448049830832"
    test    = "050451367081"
    preprod = "203918864209"
    # prod    = "476114145616"
  }

  current_account_id = lookup(local.account_ids, var.environment, data.aws_caller_identity.current.account_id)

  role_arn_pre  = "arn:aws:iam::603871901111:role/db-system-worker"
  role_arn_prod = "arn:aws:iam::232116723729:role/db-system-worker"

  selected_role_arn = var.environment == "prod" ? local.role_arn_prod : local.role_arn_pre

  is_iam_owner = terraform.workspace == var.iam_owner_workspace
}
