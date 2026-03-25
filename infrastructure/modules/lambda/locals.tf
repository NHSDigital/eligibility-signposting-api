locals {
  enable_lambda_code_signing = contains(["test", "preprod", "prod"], var.environment)
}
