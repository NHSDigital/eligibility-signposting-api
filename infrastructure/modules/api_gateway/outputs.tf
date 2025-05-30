output "rest_api_id" {
  value = aws_api_gateway_rest_api.api_gateway.id
}

output "root_resource_id" {
  value = aws_api_gateway_rest_api.api_gateway.root_resource_id
}

output "execution_arn" {
  value = aws_api_gateway_rest_api.api_gateway.execution_arn
}

output "cloudwatch_destination_arn" {
  value = aws_cloudwatch_log_group.api_gateway.arn
}

output "api_gateway_account" {
  value = aws_api_gateway_account.api_gateway
}

output "logging_policy_attachment" {
  value = aws_iam_role_policy_attachment.api_gateway_logging
}

output "iam_role_name" {
  value = aws_iam_role.api_gateway.name
}
