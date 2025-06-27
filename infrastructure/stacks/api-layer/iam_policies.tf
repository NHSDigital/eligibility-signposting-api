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
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"]
    resources = [module.eligibility_status_table.arn]
  }
}

# Attach dynamoDB write policy to external write role
resource "aws_iam_role_policy" "external_dynamodb_write_policy" {
  count  = length(aws_iam_role.write_access_role)
  name   = "DynamoDBWriteAccess"
  role   = aws_iam_role.write_access_role[count.index].id
  policy = data.aws_iam_policy_document.dynamodb_write_policy_doc.json
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

# Attach s3 write policy to kinesis firehose role
resource "aws_iam_role_policy" "kinesis_firehose_s3_write_policy" {
  name   = "S3WriteAccess"
  role   = aws_iam_role.eligibility_audit_firehose_role.id
  policy = data.aws_iam_policy_document.s3_audit_bucket_policy.json
}

# Policy doc for firehose logging
resource "aws_iam_role_policy" "kinesis_firehose_logs_policy" {
  name = "CloudWatchLogsAccess"
  role = aws_iam_role.eligibility_audit_firehose_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/kinesisfirehose/${module.eligibility_audit_firehose_delivery_stream.firehose_stream_name}:log-stream:*"
      },
      {
        Effect = "Allow",
        Action = [
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ],
        Resource = "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/kinesisfirehose/${module.eligibility_audit_firehose_delivery_stream.firehose_stream_name}"
      }
    ]
  })
}

# Attach AWSLambdaVPCAccessExecutionRole to Lambda
resource "aws_iam_role_policy_attachment" "AWSLambdaVPCAccessExecutionRole" {
  role       = aws_iam_role.eligibility_lambda_role.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

#Attach AWSLambdaBasicExecutionRole to Lambda
resource "aws_iam_role_policy_attachment" "lambda_logs_policy_attachment" {
  role       = aws_iam_role.eligibility_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
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

## KMS
data "aws_iam_policy_document" "dynamodb_kms_key_policy" {
  #checkov:skip=CKV_AWS_111: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_356: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_109: Root user needs full KMS key management
  statement {
    sid    = "EnableIamUserPermissions"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLambdaDecrypt"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.eligibility_lambda_role.arn]
    }
    actions   = ["kms:Decrypt"]
    resources = ["*"]
  }
}

resource "aws_kms_key_policy" "dynamodb_kms_key" {
  key_id = module.eligibility_status_table.dynamodb_kms_key_id
  policy = data.aws_iam_policy_document.dynamodb_kms_key_policy.json
}

data "aws_iam_policy_document" "s3_rules_kms_key_policy" {
  #checkov:skip=CKV_AWS_111: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_356: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_109: Root user needs full KMS key management
  statement {
    sid    = "EnableIamUserPermissions"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLambdaDecrypt"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.eligibility_lambda_role.arn]
    }
    actions   = ["kms:Decrypt"]
    resources = ["*"]
  }
}

resource "aws_kms_key_policy" "s3_rules_kms_key" {
  key_id = module.s3_rules_bucket.storage_bucket_kms_key_arn
  policy = data.aws_iam_policy_document.s3_rules_kms_key_policy.json
}

data "aws_iam_policy_document" "s3_audit_kms_key_policy" {
  #checkov:skip=CKV_AWS_111: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_356: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_109: Root user needs full KMS key management

  statement {
    sid    = "EnableIamUserPermissions"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLambdaFullWrite"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.eligibility_lambda_role.arn, aws_iam_role.eligibility_audit_firehose_role.arn]
    }
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey"
    ]
    resources = ["*"]
  }
}

resource "aws_kms_key_policy" "s3_audit_kms_key" {
  key_id = module.s3_audit_bucket.storage_bucket_kms_key_arn
  policy = data.aws_iam_policy_document.s3_audit_kms_key_policy.json
}

data "aws_iam_policy_document" "lambda_firehose_write_policy" {
  statement {
    sid    = "AllowLambdaToPutToFirehose"
    effect = "Allow"
    actions = [
      "firehose:PutRecord",
      "firehose:PutRecordBatch"
    ]
    resources = [
      "arn:aws:firehose:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:deliverystream/${module.eligibility_audit_firehose_delivery_stream.firehose_stream_name}"
    ]
  }
}

resource "aws_iam_role_policy" "lambda_firehose_policy" {
  name   = "LambdaFirehoseWritePolicy"
  role   = aws_iam_role.eligibility_lambda_role.id
  policy = data.aws_iam_policy_document.lambda_firehose_write_policy.json
}






