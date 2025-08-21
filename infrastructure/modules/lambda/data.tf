data "aws_caller_identity" "current" {}

data "aws_lambda_function" "existing" {
  function_name = var.lambda_func_name
  qualifier     = "$LATEST"
}
