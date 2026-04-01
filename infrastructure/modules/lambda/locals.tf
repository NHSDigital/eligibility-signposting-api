locals {
  enable_lambda_code_signing = false
  # enable_lambda_code_signing = contains(["test", "preprod", "prod"], var.environment)
  # For the next deployment ^
}
