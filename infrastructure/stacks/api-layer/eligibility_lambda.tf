module "lambda_function" {
  source               = "../../modules/lambda"
  lambda_read_role_arn = local.lambda_read_role_arn
  workspace            = local.workspace
  environment          = var.environment
}
