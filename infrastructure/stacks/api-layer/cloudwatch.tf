# CloudWatch Log Group for lambda Flow Logs
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${module.eligibility_signposting_lambda_function.aws_lambda_function_id}"
  retention_in_days = 14

  tags = {
    Name  = "lambda-execution-logs"
    Stack = local.stack_name
  }
}
