# Read-only policy for DynamoDB
data "aws_iam_policy_document" "dynamodb_read_policy_doc" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    resources = [module.eligibility_status_table.arn]
  }
}

# Attach dynamoDB read policy to Lambda role
resource "aws_iam_role_policy" "lambda_dynamodb_read_policy" {
  name   = "DynamoDBReadAccess"
  role   = aws_iam_role.eligibility_lambda_role.id
  policy = data.aws_iam_policy_document.dynamodb_read_policy_doc.json
}

# Write-only policy for DynamoDB
data "aws_iam_policy_document" "dynamodb_write_policy_doc" {
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
    resources = [module.eligibility_status_table.arn]
  }
}

# Attach dynamoDB write policy to external write role
resource "aws_iam_role_policy" "external_dynamodb_write_policy" {
  name   = "DynamoDBWriteAccess"
  role   = aws_iam_role.write_access_role.id
  policy = data.aws_iam_policy_document.dynamodb_write_policy_doc.json
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

# Policy doc for S3 Rules bucket
data "aws_iam_policy_document" "s3_rules_bucket_policy" {
  statement {
    sid = "AllowSSLRequestsOnly"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      module.s3_rules_bucket.storage_bucket_arn,
      "${module.s3_rules_bucket.storage_bucket_arn}/*",
    ]
    condition {
      test     = "Bool"
      values   = ["true"]
      variable = "aws:SecureTransport"
    }
  }
}


# Attach s3 read policy to Lambda role
resource "aws_iam_role_policy" "lambda_s3_read_policy" {
  name   = "S3ReadAccess"
  role   = aws_iam_role.eligibility_lambda_role.id
  policy = data.aws_iam_policy_document.s3_rules_bucket_policy.json
}

# Attach AWSLambdaVPCAccessExecutionRole to Lambda
resource "aws_iam_role_policy_attachment" "AWSLambdaVPCAccessExecutionRole" {
  role       = aws_iam_role.eligibility_lambda_role.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

#Attach AWSLambdaBasicExecutionRole to Lambda
resource "aws_iam_role_policy_attachment" "lambda_logs_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.eligibility_lambda_role.name
}

# Policy doc for S3 Audit bucket
data "aws_iam_policy_document" "s3_audit_bucket_policy" {
  statement {
    sid     = "AllowSSLRequestsOnly"
    actions = ["s3:*"]
    resources = [
      module.s3_audit_bucket.storage_bucket_arn,
      "${module.s3_audit_bucket.storage_bucket_arn}/*",
    ]
    condition {
      test     = "Bool"
      values   = ["true"]
      variable = "aws:SecureTransport"
    }
  }
}

# Attach s3 write policy to external write role
resource "aws_iam_role_policy" "external_s3_write_policy" {
  name   = "S3WriteAccess"
  role   = aws_iam_role.eligibility_lambda_role.id
  policy = data.aws_iam_policy_document.s3_audit_bucket_policy.json
}


