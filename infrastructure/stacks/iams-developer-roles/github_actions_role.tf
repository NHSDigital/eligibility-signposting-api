# GitHub Actions OIDC Provider
resource "aws_iam_openid_connect_provider" "github" {
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


# GitHub Actions Role
resource "aws_iam_role" "github_actions" {
  name                 = "github-actions-api-deployment-role"
  description          = "Role for GitHub Actions to deploy infrastructure via Terraform"
  permissions_boundary =  aws_iam_policy.permissions_boundary.arn
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
