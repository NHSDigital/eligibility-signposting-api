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
  }
}
