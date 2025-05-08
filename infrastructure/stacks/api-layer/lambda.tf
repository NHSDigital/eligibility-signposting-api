module "networking" {
  source = "../networking"
}


module "eligibility_signposting_lambda_function" {
  source                      = "../../modules/lambda"
  eligibility_lambda_role_arn = aws_iam_role.eligibility_lambda_role.arn
  workspace                   = local.workspace
  environment                 = var.environment
  lambda_func_name            = "eligibility_signposting_api"
  security_group_ids          = module.networking.security_group_ids
  vpc_intra_subnets           = module.networking.vpc_intra_subnets
}


