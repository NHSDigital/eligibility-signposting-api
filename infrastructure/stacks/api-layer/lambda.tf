module "eligibility_signposting_lambda_function" {
  source               = "../../modules/lambda"
  lambda_read_role_arn = aws_iam_role.lambda_read_role.arn
  workspace            = local.workspace
  environment          = var.environment
  lambda_func_name     = "eligibility_signposting_api"
}
