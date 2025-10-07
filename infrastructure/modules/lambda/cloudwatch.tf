# CloudWatch Log Group for lambda Flow Logs
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.eligibility_signposting_lambda.id}"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.lambda_cmk.arn

  tags = {
    Name  = "lambda-execution-logs"
    Stack = var.stack_name
  }
}
