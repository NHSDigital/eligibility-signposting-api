resource "aws_lambda_function" "main" {
  filename         = var.source_file
  function_name    = "${var.function_name}-${var.environment}"
  role             = var.role_arn
  handler          = var.handler
  runtime          = var.runtime
  source_code_hash = filebase64sha256(var.source_file)

  # Required for LocalStack
  publish = true
  timeout = 30
}

resource "aws_lambda_permission" "dynamodb_access" {
  statement_id  = "AllowDynamoDBAccess"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "dynamodb.amazonaws.com"
  source_arn    = var.dynamodb_arn
}
