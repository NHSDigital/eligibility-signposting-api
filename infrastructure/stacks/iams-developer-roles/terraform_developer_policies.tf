# Trust policy document
data "aws_iam_policy_document" "terraform_developer_assume_role" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    condition {
      test     = "StringLike"
      variable = "aws:PrincipalArn"
      values = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_vdselid_${var.environment}_*"
      ]
    }
  }
}

# Policy document for terraform access
# ARN(s) will need adding once they are in place / additional policies
# created in the main api stack and this removed
data "aws_iam_policy_document" "terraform_developer_policy" {
  # S3 bucket for Terraform state
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::eligibility-signposting-api-${var.environment}-tfstate",
      "arn:aws:s3:::eligibility-signposting-api-${var.environment}-tfstate/*"
    ]
  }

  # DynamoDB permissions (environment-specific)
  # Prod - only allow determination of table existence
  dynamic "statement" {
    for_each = var.environment == "prod" ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "dynamodb:DescribeTable",
        "dynamodb:ListTables",
      ]
      resources = ["*"]
    }
  }

  # Non-prod - allow full access to DynamoDB
  dynamic "statement" {
    for_each = var.environment != "prod" ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "dynamodb:CreateTable",
        "dynamodb:UpdateTable",
        "dynamodb:UpdateTableReplicaAutoScaling",
        "dynamodb:DescribeTable",
        "dynamodb:ListTables",
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:Scan",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ]
      resources = ["*"]
    }
  }

  # Lambda permissions (environment-specific)
  # Prod - only allow listing
  dynamic "statement" {
    for_each = var.environment == "prod" ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "lambda:List*",
        "lambda:Get*",
      ]
      resources = ["*"]
    }
  }

  # Non-prod - allow full access to Lambda
  dynamic "statement" {
    for_each = var.environment != "prod" ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "lambda:*"
      ]
      resources = ["*"]
    }
  }

  # CloudWatch and logging permissions
  statement {
    effect = "Allow"
    actions = [
      "logs:*",
      "cloudtrail:*",
      "cloudwatch:*"
    ]
    resources = ["*"]
  }

  # IAM permissions (restricted)
  statement {
    effect = "Allow"
    actions = [
      "iam:Get*",
      "iam:List*",
      "iam:PassRole"
    ]
    resources = ["*"]
  }

  # KMS permissions
  statement {
    effect = "Allow"
    actions = [
      "kms:Describe*",
      "kms:List*",
      "kms:Get*"
    ]
    resources = ["*"]
  }

  # SSM permissions
  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter*",
      "ssm:PutParameter"
    ]
    resources = ["*"]
  }

  # S3 permissions for application buckets
  statement {
    effect = "Allow"
    actions = [
      "s3:List*",
      "s3:Get*",
      "s3:Put*",
      "s3:CreateBucket",
      "s3:DeleteObject"
    ]
    resources = ["*"]
  }

  # API Gateway permissions
  statement {
    effect = "Allow"
    actions = [
      "apigateway:*"
    ]
    resources = ["*"]
  }

  # Read-only permissions for broader resources
  statement {
    effect = "Allow"
    actions = [
      "ec2:Describe*",
      "iam:Get*",
      "iam:List*",
      "s3:List*",
      "kms:List*"
    ]
    resources = ["*"]
  }
}

# Create policy from document
resource "aws_iam_policy" "terraform_developer_policy" {
  count       = local.is_iam_owner ? 1 : 0
  name        = "terraform-developer-policy"
  description = "Policy for terraform developers to manage resources"
  policy      = data.aws_iam_policy_document.terraform_developer_policy.json
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "terraform_developer_attachment" {
  count      = local.is_iam_owner ? 1 : 0
  role       = local.terraform_developer_role_name
  policy_arn = local.terraform_developer_policy_arn
}

data "aws_iam_role" "terraform_developer" {
  count = local.is_iam_owner ? 0 : 1
  name  = "terraform-developer-role"
}


data "aws_iam_policy" "terraform_developer_policy" {
  count = local.is_iam_owner ? 0 : 1
  arn   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/terraform-developer-policy"
}

locals {
  terraform_developer_policy_arn = local.is_iam_owner ? aws_iam_policy.terraform_developer_policy[0].arn : data.aws_iam_policy.terraform_developer_policy[0].arn

  terraform_developer_role_arn = local.is_iam_owner ? aws_iam_role.terraform_developer[0].arn : data.aws_iam_role.terraform_developer[0].arn
}
