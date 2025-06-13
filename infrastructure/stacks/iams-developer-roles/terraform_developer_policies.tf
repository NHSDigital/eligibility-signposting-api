# Trust policy document
data "aws_iam_policy_document" "terraform_developer_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
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

# Policy document for basic developer read only permissions
data "aws_iam_policy_document" "terraform_developer_policy" {

  # S3 bucket for Terraform state
  dynamic "statement" {
    for_each = var.environment != "prod" ? [1] : []
    content {
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
  }

  dynamic "statement" {
    for_each = var.environment == "prod" ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "s3:ListBucket"
      ]
      resources = [
        "arn:aws:s3:::eligibility-signposting-api-${var.environment}-tfstate",
        "arn:aws:s3:::eligibility-signposting-api-${var.environment}-tfstate/*"
      ]
    }
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
      resources = [
        "arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table:*eligibility_datastore"
      ]
    }
  }

  # Non-prod - allow full access to DynamoDB
  dynamic "statement" {
    for_each = var.environment != "prod" ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "dynamodb:DescribeTable",
        "dynamodb:ListTables",
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:Scan",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ]
      resources = [
        "arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table:*eligibility_datastore"
      ]
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
      resources = [
        "arn:aws:lambda:*:${data.aws_caller_identity.current.account_id}:function:*eligibility_signposting_api"
      ]
    }
  }

  # Non-prod - allow full access to Lambda
  dynamic "statement" {
    for_each = var.environment != "prod" ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "lambda:InvokeFunction",
        "lambda:List*",
        "lambda:Get*",
      ]
      resources = [
        "arn:aws:lambda:*:${data.aws_caller_identity.current.account_id}:function:*eligibility_signposting_api"
      ]
    }
  }


  # IAM permissions (restricted)
  statement {
    effect = "Allow"
    actions = [
      "iam:List*",
    ]
    resources = [
      "arn:aws:iam::*:role/eligibility_lambda-role*",
      "arn:aws:iam::*:role/*-api-gateway-*-role",
      "arn:aws:iam::*:role/eligibility-signposting-api-*-external-write-role"
    ]
  }

  # S3 permissions for application buckets
  statement {
    effect = "Allow"
    actions = [
      "s3:List*",
      "s3:Get*",
    ]
    resources = [
      "arn:aws:s3:::*eligibility-signposting-${var.environment}-eli-rules",
      "arn:aws:s3:::*eligibility-signposting-${var.environment}-eli-rules/*",
      "arn:aws:s3:::*eligibility-signposting-${var.environment}-eli-audit",
      "arn:aws:s3:::*eligibility-signposting-${var.environment}-eli-audit/*",
    ]
  }
}

# Create policy from document
resource "aws_iam_policy" "terraform_developer_policy" {
  name        = "terraform-developer-policy"
  description = "Policy for terraform developers to manage resources"
  policy      = data.aws_iam_policy_document.terraform_developer_policy.json
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "terraform_developer_attachment" {
  role       = aws_iam_role.terraform_developer.name
  policy_arn = aws_iam_policy.terraform_developer_policy.arn
}

data "aws_region" "current" {}
