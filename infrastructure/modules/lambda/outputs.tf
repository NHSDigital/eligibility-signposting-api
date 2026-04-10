output "aws_lambda_function_id" {
  value = aws_lambda_function.eligibility_signposting_lambda.id
}
output "aws_lambda_function_arn" {
  value = aws_lambda_function.eligibility_signposting_lambda.arn
}

output "aws_lambda_function_name" {
  value = aws_lambda_function.eligibility_signposting_lambda.function_name
}

output "aws_lambda_invoke_arn" {
  value = aws_lambda_function.eligibility_signposting_lambda.invoke_arn
}

output "lambda_cmk_arn" {
  value = aws_kms_key.lambda_cmk.arn
}

output "lambda_signing_profile_name" {
  value = aws_signer_signing_profile.lambda_signing.name
}
