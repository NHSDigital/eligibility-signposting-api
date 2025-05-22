output "aws_lambda_function_id" {
  value = aws_lambda_function.eligibility_signposting_lambda.id
}
output "aws_lambda_function_arn" {
  value = aws_lambda_function.eligibility_signposting_lambda.arn
}

output "aws_lambda_function_name" {
  value = aws_lambda_function.eligibility_signposting_lambda.function_name
}
