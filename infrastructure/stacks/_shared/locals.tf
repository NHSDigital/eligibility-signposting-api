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

  terraform_state_bucket_name = "eligibility-signposting-api-${var.environment}-tfstate"
  terraform_state_bucket_arn  = "arn:aws:s3:::eligibility-signposting-api-${var.environment}-tfstate"

  role_arn_pre  = "arn:aws:iam::603871901111:role/db-system-worker"
  role_arn_prod = "arn:aws:iam::232116723729:role/db-system-worker"

  selected_role_arn = var.environment == "prod" ? local.role_arn_prod : local.role_arn_pre
}
