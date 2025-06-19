data "aws_security_group" "main_sg" {
  name = "main-security-group"
}

data "aws_subnet" "private_subnets" {
  for_each = toset(["private-subnet-1", "private-subnet-2", "private-subnet-3"])

  tags = {
    Name = each.value
  }
}

module "eligibility_signposting_lambda_function" {
  source                        = "../../modules/lambda"
  eligibility_lambda_role_arn   = aws_iam_role.eligibility_lambda_role.arn
  workspace                     = local.workspace
  environment                   = var.environment
  lambda_func_name              = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}eligibility_signposting_api"
  security_group_ids            = [data.aws_security_group.main_sg.id]
  vpc_intra_subnets             = [for v in data.aws_subnet.private_subnets : v.id]
  file_name                     = "../../../dist/lambda.zip"
  handler                       = "eligibility_signposting_api.app.lambda_handler"
  eligibility_rules_bucket_name = module.s3_rules_bucket.storage_bucket_name
  eligibility_status_table_name = module.eligibility_status_table.table_name
  log_level                     = "INFO"
  stack_name                    = local.stack_name
}
