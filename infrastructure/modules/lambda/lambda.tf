resource "aws_lambda_function" "eligibility_signposting_lambda" {
  #checkov:skip=CKV_AWS_116: No deadletter queue is configured for this Lambda function, yet
  #checkov:skip=CKV_AWS_115: Concurrent execution limit will be set at APIM level, not at Lambda level
  #checkov:skip=CKV_AWS_272: Skipping code signing but flagged to create ticket to investigate on ELI-238
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
      PERSON_TABLE_NAME          = var.eligibility_status_table_name,
      RULES_BUCKET_NAME          = var.eligibility_rules_bucket_name,
      KINESIS_AUDIT_STREAM_TO_S3 = var.kinesis_audit_stream_to_s3_name
      ENV                        = var.environment
      LOG_LEVEL                  = var.log_level
    }
  }

  kms_key_arn = aws_kms_key.lambda_cmk.arn

  vpc_config {
    subnet_ids         = var.vpc_intra_subnets
    security_group_ids = var.security_group_ids
  }

  tracing_config {
    mode = "Active"
  }
}
