output "terraform_developer_role_arn" {
  description = "ARN of the Terraform developer role"
  value       = local.terraform_developer_role_arn
}

output "assume_role_command" {
  description = "Command to assume the Terraform developer role"
  value       = "aws sts assume-role --role-arn ${local.terraform_developer_role_arn} --role-session-name TerraformSession"
}

output "permissions_boundary_arn" {
  description = "ARN of the permissions boundary policy"
  value       = local.permissions_boundary_arn
}
