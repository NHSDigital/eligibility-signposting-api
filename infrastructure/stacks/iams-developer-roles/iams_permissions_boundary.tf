# Policy document for Permissions boundary
data "aws_iam_policy_document" "permissions_boundary" {
  #checkov:skip=CKV2_AWS_40: Ensure AWS IAM policy does not allow full IAM privileges
  statement {
    sid    = "RestrictRegion"
    effect = "Allow"

    actions = [
      "acm:*",
      "application-autoscaling:*",
      "apigateway:*",
      "cloudtrail:*",
      "cloudwatch:*",
      "config:*",
      "dynamodb:*",
      "ec2:*",
      "events:*",
      "firehose:*",
      "glue:*",
      "health:*",
      "iam:*",
      "kms:*",
      "lambda:*",
      "logs:*",
      "network-firewall:*",
      "pipes:*",
      "s3:*",
      "schemas:*",
      "sns:*",
      "servicequotas:*",
      "ssm:*",
      "states:*",
      "support:*",
      "sqs:*",
      "tag:*",
      "trustedadvisor:*"
    ]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.default_aws_region]
    }
  }

  statement {
    sid    = "DenyPrivEsculationViaIamRoles"
    effect = "Deny"
    actions = ["iam:*"]
    resources = ["*"]
    condition {
      test     = "ArnLike"
      variable = "iam:PolicyARN"
      values   = ["arn:aws:iam::*:policy/${upper(var.project_name)}-*"]
    }
  }

  statement {
    sid    = "DenyPrivEsculationViaIamProfiles"
    effect = "Deny"
    actions = ["iam:*"]
    resources = ["arn:aws:iam::*:role/${upper(var.project_name)}-*"]
  }
}

# Permissions Boundary policy created only in owner workspace
resource "aws_iam_policy" "permissions_boundary" {
  count       = local.is_iam_owner ? 1 : 0
  name        = "${upper(var.project_name)}-PermissionsBoundary"
  description = "Allows access to AWS services in the regions the client uses only"
  policy      = data.aws_iam_policy_document.permissions_boundary.json

  tags = merge(
    local.tags,
    {
      Stack = "iams-developer-roles"
    }
  )
}

# Data source for non-owner workspaces (using ARN)
data "aws_iam_policy" "permissions_boundary" {
  count = local.is_iam_owner ? 0 : 1
  arn   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${upper(var.project_name)}-PermissionsBoundary"
}

# Local to always reference the correct policy ARN
locals {
  permissions_boundary_arn = local.is_iam_owner ? aws_iam_policy.permissions_boundary[0].arn : data.aws_iam_policy.permissions_boundary[0].arn
}
