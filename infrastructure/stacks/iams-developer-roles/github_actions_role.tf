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
  permissions_boundary = aws_iam_policy.permissions_boundary.arn
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


# GitHub Actions IAM Bootstrap Role
# It can update the main deployment role's policies but cannot modify itself.
resource "aws_iam_role" "github_actions_iam_bootstrap" {
  name                 = "github-actions-iam-bootstrap-role"
  description          = "Role for GitHub Actions to deploy IAM infrastructure (iams-developer-roles stack only)"
  permissions_boundary = aws_iam_policy.iam_bootstrap_permissions_boundary.arn
  path                 = "/service-roles/"

  assume_role_policy = data.aws_iam_policy_document.github_actions_iam_bootstrap_assume_role.json

  tags = merge(
    local.tags,
    {
      Name = "github-actions-iam-bootstrap-role"
    }
  )
}

data "aws_iam_policy_document" "github_actions_iam_bootstrap_assume_role" {
  statement {
    sid     = "OidcAssumeRoleForIamBootstrap"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type = "Federated"
      identifiers = [
        aws_iam_openid_connect_provider.github.arn
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Only allow from main branch (and events triggered from main)
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [
        "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main",
        "repo:${var.github_org}/${var.github_repo}:environment:*",
      ]
    }

    # Only allow from the IAM bootstrap and base deployment workflows
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:job_workflow_ref"
      values   = [
        "${var.github_org}/${var.github_repo}/.github/workflows/iam-bootstrap-deploy.yaml@*",
        "${var.github_org}/${var.github_repo}/.github/workflows/base-deploy.yml@*",
        "${var.github_org}/${var.github_repo}/.github/workflows/cicd-2-publish.yaml@*",
      ]
    }
  }
}
