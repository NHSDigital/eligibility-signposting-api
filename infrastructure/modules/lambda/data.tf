data "aws_caller_identity" "current" {}

data "aws_lambda_function" "existing" {
  function_name = aws_lambda_function.eligibility_signposting_lambda.function_name
}
