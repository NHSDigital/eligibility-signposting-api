# Read-only policy for DynamoDB
data "aws_iam_policy_document" "dynamodb_read_policy" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    resources = [module.eligibility_status_table.arn]
  }
}

# Write-only policy for DynamoDB
data "aws_iam_policy_document" "dynamodb_write_policy" {
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
    resources = [module.eligibility_status_table.arn]
  }
}

# Attach read policy to Lambda role (only in IAM default workspace)
resource "aws_iam_role_policy" "lambda_read_policy" {
  count  = local.is_iam_owner ? 1 : 0
  name   = "DynamoDBReadAccess"
  role   = local.lambda_read_role
  policy = data.aws_iam_policy_document.dynamodb_read_policy.json
}

# Attach write policy to external write role (only in IAM default workspace)
resource "aws_iam_role_policy" "external_write_policy" {
  count  = local.is_iam_owner ? 1 : 0
  name   = "DynamoDBWriteAccess"
  role   = local.write_access_role
  policy = data.aws_iam_policy_document.dynamodb_write_policy.json
}


# Deny all S3 actions on the access logs bucket unless requests use secure (SSL) transport.
data "aws_iam_policy_document" "storage_bucket_access_logs_policy" {
  statement {
    sid = "AllowSSLRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      module.s3_rules_bucket.storage_bucket_access_logs_arn,
      "${module.s3_rules_bucket.storage_bucket_access_logs_arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test = "Bool"
      values = [
        "false",
      ]

      variable = "aws:SecureTransport"
    }
  }
}

resource "aws_s3_bucket_policy" "storage_bucket_access_logs_policy" {
  bucket = module.s3_rules_bucket.storage_bucket_access_logs_id
  policy = data.aws_iam_policy_document.storage_bucket_access_logs_policy.json
}


