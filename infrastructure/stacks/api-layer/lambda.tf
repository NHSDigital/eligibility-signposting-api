module "networking" {
  source = "../networking"
}


module "eligibility_signposting_lambda_function" {
  source                      = "../../modules/lambda"
  eligibility_lambda_role_arn = aws_iam_role.eligibility_lambda_role.arn
  workspace                   = local.workspace
  environment                 = var.environment
  lambda_func_name            = "eli_signposting_api"
  security_group_ids          = module.networking.security_group_ids
  vpc_intra_subnets           = module.networking.vpc_intra_subnets
  file_name                   = "src/lambda_function_payload.zip"
  handler                     = "lambda_function1.lambda_handler"
  lambda_app_source_file      = "src/lambda_function1.py"
  lambda_app_zip_output_path  = "src/lambda_function_payload.zip"
}

