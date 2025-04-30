output "terraform_developer_role_arn" {
  description = "ARN of the Terraform developer role"
  value       = aws_iam_role.terraform_developer.arn
}

output "assume_role_command" {
  description = "Command to assume the Terraform developer role"
  value       = "aws sts assume-role --role-arn ${aws_iam_role.terraform_developer.arn} --role-session-name TerraformSession"
}

output "permissions_boundary_arn" {
  description = "ARN of the permissions boundary policy"
  value       = aws_iam_policy.permissions_boundary.arn
}
