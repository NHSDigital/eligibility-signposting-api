# CloudWatch Log Group for lambda Flow Logs
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${module.eligibility_signposting_lambda_function.aws_lambda_function_id}"
  retention_in_days = 365
  kms_key_id        = module.eligibility_signposting_lambda_function.lambda_cmk_arn

  tags = {
    Name  = "lambda-execution-logs"
    Stack = local.stack_name
  }
}

resource "aws_cloudwatch_log_group" "firehose_audit" {
  name              = "/aws/kinesisfirehose/${var.project_name}-${var.environment}-audit"
  retention_in_days = 365
  kms_key_id        = module.eligibility_audit_firehose_delivery_stream.kinesis_firehose_cmk_arn

  tags = {
    Name  = "kinesis-firehose-logs"
    Stack = local.stack_name
  }
}

resource "aws_cloudwatch_log_stream" "firehose_audit_stream" {
  name           = "audit_stream_log"
  log_group_name = aws_cloudwatch_log_group.firehose_audit.name
}
