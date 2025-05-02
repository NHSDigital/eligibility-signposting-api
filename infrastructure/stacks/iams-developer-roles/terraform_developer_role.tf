resource "aws_iam_role" "terraform_developer" {
  count              = local.is_iam_owner ? 1 : 0
  name               = "terraform-developer-role"
  description        = "Role for developers to plan and apply Terraform changes"
  assume_role_policy = data.aws_iam_policy_document.terraform_developer_assume_role.json
  permissions_boundary = local.permissions_boundary_arn  # Attach permissions boundary
  max_session_duration = 14400  # 4 hours

  tags = merge(
    local.tags,
    {
      Name = "terraform-developer-role"
    }
  )
}

locals {
  terraform_developer_role_name = local.is_iam_owner ? aws_iam_role.terraform_developer[0].name : data.aws_iam_role.terraform_developer[0].name
}

