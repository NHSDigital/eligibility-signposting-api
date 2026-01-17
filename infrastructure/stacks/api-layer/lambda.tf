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
  source                                    = "../../modules/lambda"
  eligibility_lambda_role_arn               = aws_iam_role.eligibility_lambda_role.arn
  eligibility_lambda_role_name              = aws_iam_role.eligibility_lambda_role.name
  workspace                                 = local.workspace
  environment                               = var.environment
  runtime                                   = "python3.13"
  lambda_func_name                          = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}eligibility_signposting_api"
  security_group_ids = [data.aws_security_group.main_sg.id]
  vpc_intra_subnets                         = [for v in data.aws_subnet.private_subnets : v.id]
  file_name                                 = "../../../dist/lambda.zip"
  handler                                   = "eligibility_signposting_api.app.lambda_handler"
  eligibility_rules_bucket_name             = module.s3_rules_bucket.storage_bucket_name
  eligibility_consumer_mappings_bucket_name = module.s3_consumer_mappings_bucket.storage_bucket_name
  eligibility_status_table_name             = module.eligibility_status_table.table_name
  kinesis_audit_stream_to_s3_name           = module.eligibility_audit_firehose_delivery_stream.firehose_stream_name
  hashing_secret_name                       = module.secrets_manager.aws_hashing_secret_name
  lambda_insights_extension_version         = 38
  log_level                                 = "INFO"
  enable_xray_patching                      = "true"
  stack_name                                = local.stack_name
  provisioned_concurrency_count             = 5
  api_domain_name                           = local.api_domain_name
}

# -----------------------------------------------------------------------------
# Secret rotation lambdas
# -----------------------------------------------------------------------------

# 1. Generator Lambda
data "archive_file" "create_zip" {
  type        = "zip"
  source_file = "${path.module}/scripts/create_pending_secret.py"
  output_path = "${path.module}/scripts/create_pending_secret.zip"
}

resource "aws_lambda_function" "create_secret_lambda" {
  #checkov:skip=CKV_AWS_116: No deadletter queue is required for this Lambda function
  #checkov:skip=CKV_AWS_272: Skipping code signing but flagged to create ticket to investigate on ELI-238
  #checkov:skip=CKV_AWS_50: No x-ray needed for this function
  #checkov:skip=CKV_AWS_173: No encryption needed for the secret name

  filename                       = data.archive_file.create_zip.output_path
  function_name                  = "${terraform.workspace}-CreatePendingSecretFunction"
  role                           = aws_iam_role.rotation_lambda_role.arn
  handler                        = "create_pending_secret.lambda_handler"
  runtime                        = "python3.13"
  timeout                        = 30
  reserved_concurrent_executions = 1
  environment {
    variables = { SECRET_NAME = module.secrets_manager.aws_hashing_secret_name }
  }
  vpc_config {
    subnet_ids = [for s in data.aws_subnet.private_subnets : s.id]
    security_group_ids = [data.aws_security_group.main_sg.id]
  }
}

# 2. Promoter Lambda
data "archive_file" "promote_zip" {
  type        = "zip"
  source_file = "${path.module}/scripts/promote_to_current.py"
  output_path = "${path.module}/scripts/promote_to_current.zip"
}

resource "aws_lambda_function" "promote_secret_lambda" {
  #checkov:skip=CKV_AWS_116: No deadletter queue is required for this Lambda function
  #checkov:skip=CKV_AWS_272: Skipping code signing but flagged to create ticket to investigate on ELI-238
  #checkov:skip=CKV_AWS_50: No x-ray needed for this function
  #checkov:skip=CKV_AWS_173: No encryption needed for the secret name

  filename                       = data.archive_file.promote_zip.output_path
  function_name                  = "${terraform.workspace}-PromoteToCurrentFunction"
  role                           = aws_iam_role.rotation_lambda_role.arn
  handler                        = "promote_to_current.lambda_handler"
  runtime                        = "python3.13"
  timeout                        = 30
  reserved_concurrent_executions = 1
  environment {
    variables = { SECRET_NAME = module.secrets_manager.aws_hashing_secret_name }
  }
  vpc_config {
    subnet_ids = [for s in data.aws_subnet.private_subnets : s.id]
    security_group_ids = [data.aws_security_group.main_sg.id]
  }
}
