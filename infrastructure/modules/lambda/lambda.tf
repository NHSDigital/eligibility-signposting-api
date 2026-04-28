resource "aws_lambda_function" "eligibility_signposting_lambda" {
  #checkov:skip=CKV_AWS_116: No deadletter queue is configured for this Lambda function, as the requests are synchronous
  #checkov:skip=CKV_AWS_115: Concurrent execution limit will be set at APIM level, not at Lambda level
  #checkov:skip=CKV_AWS_272: Code signing not yet enforced in prod - tracked for removal when prod enforcement is enabled
  # If the file is not in the current working directory you will need to include a
  # path.module in the filename.
  filename      = var.file_name
  function_name = var.lambda_func_name
  role          = var.eligibility_lambda_role_arn
  handler       = var.handler

  source_code_hash = filebase64sha256(var.file_name)

  code_signing_config_arn = contains(var.environments_with_signing, var.environment) ? aws_lambda_code_signing_config.signing_config.arn : null

  runtime     = var.runtime
  timeout     = 30
  memory_size = 2048

  environment {
    variables = {
      PERSON_TABLE_NAME            = var.eligibility_status_table_name,
      RULES_BUCKET_NAME            = var.eligibility_rules_bucket_name,
      CONSUMER_MAPPING_BUCKET_NAME = var.eligibility_consumer_mappings_bucket_name,
      KINESIS_AUDIT_STREAM         = var.kinesis_audit_stream_name,
      ENV                          = var.environment,
      LOG_LEVEL                    = var.log_level,
      ENABLE_XRAY_PATCHING         = var.enable_xray_patching,
      API_DOMAIN_NAME              = var.api_domain_name,
      HASHING_SECRET_NAME          = var.hashing_secret_name,
    }
  }

  kms_key_arn = aws_kms_key.lambda_cmk.arn

  publish = true

  vpc_config {
    subnet_ids         = var.vpc_intra_subnets
    security_group_ids = var.security_group_ids
  }

  layers = compact([
    # LambdaInsightsExtension excluded: incompatible with Lambda code signing enforcement.
    # AWS signs the layer with an internal profile not available via the API.
  ])


  tracing_config {
    mode = "Active"
  }
}

# lambda alias required for provisioning concurrency
resource "aws_lambda_alias" "campaign_alias" {
  count            = var.environment == "prod" || var.environment == "preprod" ? 1 : 0
  name             = "live"
  function_name    = aws_lambda_function.eligibility_signposting_lambda.function_name
  function_version = aws_lambda_function.eligibility_signposting_lambda.version
}

# provisioned concurrency - number of pre-warmed lambda containers
resource "aws_lambda_provisioned_concurrency_config" "campaign_pc" {
  count                             = var.environment == "prod" || var.environment == "preprod" ? 1 : 0
  function_name                     = var.lambda_func_name
  qualifier                         = aws_lambda_alias.campaign_alias[0].name
  provisioned_concurrent_executions = var.provisioned_concurrency_count
}
