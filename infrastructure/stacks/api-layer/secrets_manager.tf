module "secrets_manager" {
  source = "../../modules/secrets_manager"
  count = length(aws_iam_role.write_access_role)
  external_write_access_role_arn = aws_iam_role.write_access_role[count.index].arn
  external_write_access_role_name = aws_iam_role.write_access_role[count.index].name
  environment  = var.environment
  stack_name   = local.stack_name
  workspace    = terraform.workspace
}
