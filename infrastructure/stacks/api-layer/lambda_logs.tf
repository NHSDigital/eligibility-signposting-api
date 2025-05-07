# CloudWatch Log Group for lambda Flow Logs
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${module.eligibility_signposting_lambda_function.aws_lambda_function_id}"
  retention_in_days = 14

  tags = {
    Name  = "lambda-execution-logs"
    Stack = "api-layer" #TODO
  }
}


resource "aws_iam_role_policy_attachment" "lambda_logs_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_read_role.name
}
