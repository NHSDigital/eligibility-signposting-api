resource "aws_lambda_function" "eligibility_signposting_lambda" {
  # If the file is not in the current working directory you will need to include a
  # path.module in the filename.
  filename      = var.file_name
  function_name = var.lambda_func_name
  role          = var.eligibility_lambda_role_arn
  handler       = var.handler

  source_code_hash = filebase64sha256(var.file_name)

  runtime     = "python3.13"
  timeout     = 30
  memory_size = 128 # Default

  environment {
    variables = {
      ELIGIBILITY_TABLE_NAME = var.eligibility_status_table_name,
      RULES_BUCKET_NAME      = var.eligibility_rules_bucket_name,
      ENV                    = var.environment
    }
  }
  vpc_config {
    subnet_ids         = var.vpc_intra_subnets
    security_group_ids = var.security_group_ids
  }
}
