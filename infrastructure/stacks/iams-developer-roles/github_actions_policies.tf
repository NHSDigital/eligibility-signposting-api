# Terraform State Management Policy
# Create policies only in the IAM default workspace
resource "aws_iam_policy" "terraform_state" {
  count       = local.is_iam_owner ? 1 : 0
  name        = "terraform-state-management"
  description = "Policy granting access to S3 bucket for Terraform state"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        Resource = [
          "${local.terraform_state_bucket_arn}",
          "${local.terraform_state_bucket_arn}/*"
        ]
      }
    ]
  })

  tags = merge(
    local.tags,
    {
      Name = "terraform-state-management"
    }
  )
}

# API Infrastructure Management Policy
resource "aws_iam_policy" "api_infrastructure" {
  count       = local.is_iam_owner ? 1 : 0
  name        = "api-infrastructure-management"
  description = "Policy granting permissions to manage API infrastructure"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          # Lambda permissions
          "lambda:*",

          # DynamoDB permissions
          "dynamodb:*",

          # API Gateway permissions
          "apigateway:*",

          # S3 permissions
          "s3:*",

          # IAM permissions (scoped to resources with specific path prefix)
          "iam:Get*",
          "iam:List*",
          "iam:Create*",
          "iam:Update*",
          "iam:Delete*",
        ],
        Resource = "*"
      }
    ]
  })

  tags = merge(
    local.tags,
    {
      Name = "api-infrastructure-management"
    }
  )
}

# Data sources for policies in non-default workspaces
data "aws_iam_policy" "terraform_state" {
  count = local.is_iam_owner ? 0 : 1
  arn   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/service-policies/terraform-state-management"
}

data "aws_iam_policy" "api_infrastructure" {
  count = local.is_iam_owner ? 0 : 1
  arn   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/service-policies/api-infrastructure-management"
}

# Assume role policy document for GitHub Actions
data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    sid    = "OidcAssumeRoleWithWebIdentity"
    effect = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type = "Federated"
      identifiers = [
        local.aws_iam_openid_connect_provider_arn
      ]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = ["repo:${var.github_org}/${var.github_repo}:*"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values = ["sts.amazonaws.com"]
    }
  }
}

# Attach the policies to the role (only in default workspace)
resource "aws_iam_role_policy_attachment" "terraform_state" {
  count      = local.is_iam_owner ? 1 : 0
  role       = local.github_actions_iam_role_name
  policy_arn = local.terraform_state_iam_policy_arn
}

resource "aws_iam_role_policy_attachment" "api_infrastructure" {
  count      = local.is_iam_owner ? 1 : 0
  role       = local.github_actions_iam_role_name
  policy_arn = local.api_infrastructure_iam_policy_arn
}

locals {
  terraform_state_iam_policy_arn = local.is_iam_owner ? aws_iam_policy.terraform_state[0].arn : data.aws_iam_policy.terraform_state[0].arn
  api_infrastructure_iam_policy_arn = local.is_iam_owner ? aws_iam_policy.api_infrastructure[0].arn : data.aws_iam_policy.api_infrastructure[0].arn
}
