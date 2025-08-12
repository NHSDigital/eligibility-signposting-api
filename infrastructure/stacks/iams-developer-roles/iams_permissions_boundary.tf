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
      "trustedadvisor:*",
      "xray:*"
    ]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.default_aws_region]
    }
  }

  # Allow access to IAM actions for us-east-1 region only
  statement {
    sid       = "AllowIamActionsInUsEast1"
    effect    = "Allow"
    actions   = ["iam:*"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = ["us-east-1"]
    }
  }

  statement {
    sid       = "DenyPrivEsculationViaIamRoles"
    effect    = "Deny"
    actions   = ["iam:*"]
    resources = ["*"]
    condition {
      test     = "ArnLike"
      variable = "iam:PolicyARN"
      values   = ["arn:aws:iam::*:policy/${upper(var.project_name)}-*"]
    }
  }

  statement {
    sid       = "DenyPrivEsculationViaIamProfiles"
    effect    = "Deny"
    actions   = ["iam:*"]
    resources = ["arn:aws:iam::*:role/${upper(var.project_name)}-*"]
  }
}

# Permissions Boundary policy
resource "aws_iam_policy" "permissions_boundary" {
  name        = "${local.stack_name}-${upper(var.project_name)}-PermissionsBoundary"
  description = "Allows access to AWS services in the regions the client uses only"
  policy      = data.aws_iam_policy_document.permissions_boundary.json

  tags = merge(
    local.tags,
    {
      Stack = "iams-developer-roles"
    }
  )
}
