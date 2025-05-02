# GitHub Actions OIDC Provider: create only in default workspace
resource "aws_iam_openid_connect_provider" "github" {
  count           = local.is_iam_owner ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = merge(
    local.tags,
    {
      Name = "github-actions-oidc-provider"
    }
  )
}

# Data source to reference existing OIDC provider in non-default workspaces
data "aws_iam_openid_connect_provider" "github" {
  count = local.is_iam_owner ? 0 : 1
  url   = "https://token.actions.githubusercontent.com"
}

# GitHub Actions Role: create only in default workspace
resource "aws_iam_role" "github_actions" {
  count                = local.is_iam_owner ? 1 : 0
  name                 = "github-actions-api-deployment-role"
  description          = "Role for GitHub Actions to deploy infrastructure via Terraform"
  permissions_boundary = local.permissions_boundary_arn
  path                 = "/service-roles/"

  # Trust policy allowing GitHub Actions to assume the role
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json

  tags = merge(
    local.tags,
    {
      Name = "github-actions-api-deployment-role"
    }
  )
}

# Data source to reference existing GitHub Actions role in non-default workspaces
data "aws_iam_role" "github_actions" {
  count = local.is_iam_owner ? 0 : 1
  name  = "github-actions-api-deployment-role"
}

locals {
  github_actions_iam_role_name = local.is_iam_owner ? aws_iam_role.github_actions[0].name : data.aws_iam_role.github_actions[0].name
  aws_iam_openid_connect_provider_arn=local.is_iam_owner ? aws_iam_openid_connect_provider.github[0].arn : data.aws_iam_openid_connect_provider.github[0].arn
}
