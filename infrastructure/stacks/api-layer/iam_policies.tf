# Read-only policy for DynamoDB
data "aws_iam_policy_document" "dynamodb_read_policy_doc" {
  statement {
    actions = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
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
    actions = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"]
    resources = [module.eligibility_status_table.arn]
  }
}

# Specific Dynamo resource KMS access policy
data "aws_iam_policy_document" "dynamo_kms_access_policy_doc" {
  statement {
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey"
    ]
    resources = [
      module.eligibility_status_table.dynamodb_kms_key_arn
    ]
  }
}

# Attach dynamoDB write policy to external write role
resource "aws_iam_role_policy" "external_dynamodb_write_policy" {
  count = length(aws_iam_role.write_access_role)
  name   = "DynamoDBWriteAccess"
  role   = aws_iam_role.write_access_role[count.index].id
  policy = data.aws_iam_policy_document.dynamodb_write_policy_doc.json
}

# Attach dynamo KMS policy to external write role
resource "aws_iam_role_policy" "external_kms_access_policy" {
  count = length(aws_iam_role.write_access_role)
  name   = "KMSAccessForDynamoDB"
  role   = aws_iam_role.write_access_role[count.index].id
  policy = data.aws_iam_policy_document.dynamo_kms_access_policy_doc.json
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
      values = ["true"]
      variable = "aws:SecureTransport"
    }
  }
}

# ensure only secure transport is allowed

resource "aws_s3_bucket_policy" "rules_s3_bucket" {
  bucket = module.s3_rules_bucket.storage_bucket_id
  policy = data.aws_iam_policy_document.rules_s3_bucket_policy.json
}

data "aws_iam_policy_document" "rules_s3_bucket_policy" {
  statement {
    sid = "AllowSslRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      module.s3_rules_bucket.storage_bucket_arn,
      "${module.s3_rules_bucket.storage_bucket_arn}/*",
    ]
    principals {
      type = "*"
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

# Policy doc for S3 Consumer Mappings bucket
data "aws_iam_policy_document" "s3_consumer_mapping_bucket_policy" {
  statement {
    sid = "AllowSSLRequestsOnly"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      module.s3_consumer_mappings_bucket.storage_bucket_arn,
      "${module.s3_consumer_mappings_bucket.storage_bucket_arn}/*",
    ]
    condition {
      test     = "Bool"
      values = ["true"]
      variable = "aws:SecureTransport"
    }
  }
}

# ensure only secure transport is allowed

resource "aws_s3_bucket_policy" "consumer_mapping_s3_bucket" {
  bucket = module.s3_consumer_mappings_bucket.storage_bucket_id
  policy = data.aws_iam_policy_document.s3_consumer_mapping_bucket_policy.json
}

data "aws_iam_policy_document" "consumer_mapping_s3_bucket_policy" {
  statement {
    sid = "AllowSslRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      module.s3_consumer_mappings_bucket.storage_bucket_arn,
      "${module.s3_consumer_mappings_bucket.storage_bucket_arn}/*",
    ]
    principals {
      type = "*"
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

# audit bucket
resource "aws_s3_bucket_policy" "audit_s3_bucket" {
  bucket = module.s3_audit_bucket.storage_bucket_id
  policy = data.aws_iam_policy_document.audit_s3_bucket_policy.json
}

data "aws_iam_policy_document" "audit_s3_bucket_policy" {
  statement {
    sid = "AllowSslRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      module.s3_audit_bucket.storage_bucket_arn,
      "${module.s3_audit_bucket.storage_bucket_arn}/*",
    ]
    principals {
      type = "*"
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

# Attach s3 read policy to Lambda role
resource "aws_iam_role_policy" "lambda_s3_rules_read_policy" {
  name   = "S3RulesReadAccess"
  role   = aws_iam_role.eligibility_lambda_role.id
  policy = data.aws_iam_policy_document.s3_rules_bucket_policy.json
}

resource "aws_iam_role_policy" "lambda_s3_mapping_read_policy" {
  name   = "S3ConsumerMappingReadAccess"
  role   = aws_iam_role.eligibility_lambda_role.id
  policy = data.aws_iam_policy_document.s3_consumer_mapping_bucket_policy.json
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

#Attach CloudWatchLambdaInsightsExecutionRolePolicy to lambda for enhanced monitoring
resource "aws_iam_role_policy_attachment" "lambda_insights_policy" {
  role       = aws_iam_role.eligibility_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"
}

# Policy doc for S3 Audit bucket
data "aws_iam_policy_document" "s3_audit_bucket_policy" {
  statement {
    sid = "AllowSSLRequestsOnly"
    actions = ["s3:*"]
    resources = [
      module.s3_audit_bucket.storage_bucket_arn,
      "${module.s3_audit_bucket.storage_bucket_arn}/*",
    ]
    condition {
      test     = "Bool"
      values = ["true"]
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
      type = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLambdaDecrypt"
    effect = "Allow"
    principals {
      type = "AWS"
      identifiers = [aws_iam_role.eligibility_lambda_role.arn]
    }
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
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
      type = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLambdaDecrypt"
    effect = "Allow"
    principals {
      type = "AWS"
      identifiers = [aws_iam_role.eligibility_lambda_role.arn]
    }
    actions = ["kms:Decrypt"]
    resources = ["*"]
  }
}

resource "aws_kms_key_policy" "s3_rules_kms_key" {
  key_id = module.s3_rules_bucket.storage_bucket_kms_key_id
  policy = data.aws_iam_policy_document.s3_rules_kms_key_policy.json
}

resource "aws_iam_role_policy" "splunk_firehose_policy" {
  #checkov:skip=CKV_AWS_290: Firehose requires write access to dynamic log streams without static constraints
  #checkov:skip=CKV_AWS_355: Firehose logging requires wildcard resource for CloudWatch log groups/streams
  name = "splunk-firehose-policy"
  role = aws_iam_role.splunk_firehose_assume_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # Allow Firehose to write to S3 backup bucket
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ],
        Resource = [
          module.s3_firehose_backup_bucket.storage_bucket_arn,
          "${module.s3_firehose_backup_bucket.storage_bucket_arn}/*"
        ]
      },
      # Allow Firehose to use KMS key for S3 encryption
      {
        Effect = "Allow",
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ],
        Resource = [module.s3_firehose_backup_bucket.storage_bucket_kms_key_arn]
      },
      # Allow logging to CloudWatch
      {
        Effect = "Allow",
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream",
          "logs:CreateLogGroup"
        ],
        Resource = "*"
      }
    ]
  })
}

data "aws_iam_policy_document" "s3_audit_kms_key_policy" {
  #checkov:skip=CKV_AWS_111: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_356: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_109: Root user needs full KMS key management

  # Allow root user to have full control
  statement {
    sid    = "EnableIamUserPermissions"
    effect = "Allow"
    principals {
      type = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions = ["kms:*"]
    resources = ["*"]
  }
  # Allow Lambda, Firehose, and external write roles to use the KMS key
  statement {
    sid    = "AllowAuditKeyAccess"
    effect = "Allow"
    principals {
      type = "AWS"
      identifiers = concat(
        [
          aws_iam_role.eligibility_lambda_role.arn,
          aws_iam_role.eligibility_audit_firehose_role.arn
        ],
        aws_iam_role.write_access_role[*].arn
      )
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
  key_id = module.s3_audit_bucket.storage_bucket_kms_key_id
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

data "aws_iam_policy_document" "lambda_xray_tracing_permissions_policy" {
  statement {
    sid    = "AllowLambdaToPutToXRay"
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_xray_tracing_policy" {
  name   = "LambdaXRayWritePolicy"
  role   = aws_iam_role.eligibility_lambda_role.id
  policy = data.aws_iam_policy_document.lambda_xray_tracing_permissions_policy.json
}

# KMS Key Policy for SNS encryption
resource "aws_kms_key_policy" "sns_encryption_key_policy" {
  key_id = aws_kms_key.sns_encryption_key.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableIAMRootPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowCloudWatchAlarmsAccess"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowSNSServiceAccess"
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy doc for external write role to read, move, and tag objects in S3
data "aws_iam_policy_document" "external_s3_read_move_policy_doc" {
  statement {
    sid    = "ListBucket"
    actions = [
      "s3:ListBucket",
      "s3:ListBucketVersions"
    ]
    resources = [
      module.s3_audit_bucket.storage_bucket_arn
    ]
  }

  statement {
    sid    = "ReadMoveTagObjects"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetObjectTagging",
      "s3:PutObjectTagging",
      "s3:PutObject"
    ]
    resources = [
      "${module.s3_audit_bucket.storage_bucket_arn}/*"
    ]
  }
}

# Attach external S3 read, move & tagging policy to external write role
resource "aws_iam_role_policy" "external_s3_read_move_policy" {
  count  = length(aws_iam_role.write_access_role)
  name   = "S3ReadMoveTagAccess"
  role   = aws_iam_role.write_access_role[count.index].id
  policy = data.aws_iam_policy_document.external_s3_read_move_policy_doc.json
}

# KMS access policy for S3 audit bucket from external write role
data "aws_iam_policy_document" "external_role_s3_audit_kms_access_policy" {
  statement {
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    resources = [
      module.s3_audit_bucket.storage_bucket_kms_key_arn,
      module.eligibility_audit_firehose_delivery_stream.kinesis_firehose_cmk_arn
    ]
  }
}

# Attach KMS policy to external write role
resource "aws_iam_role_policy" "external_audit_kms_access_policy" {
  count = length(aws_iam_role.write_access_role)
  name   = "KMSAccessForS3Audit"
  role   = aws_iam_role.write_access_role[count.index].id
  policy = data.aws_iam_policy_document.external_role_s3_audit_kms_access_policy.json
}

# IAM policy document for Lambda secret access
data "aws_iam_policy_document" "secrets_access_policy" {
  statement {
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]

    resources = [
      module.secrets_manager.aws_hashing_secret_arn
    ]
  }
}

# Attach secret read policy to Lambda role
resource "aws_iam_role_policy" "lambda_secret_read_policy_attachment" {
  name   = "LambdaSecretReadAccess"
  role   = aws_iam_role.eligibility_lambda_role.id
  policy = data.aws_iam_policy_document.secrets_access_policy.json
}

# Attach secret read policy to external write role
resource "aws_iam_role_policy" "external_secret_read_policy_attachment" {
  count = length(aws_iam_role.write_access_role)
  name   = "ExternalSecretReadAccess"
  role   = aws_iam_role.write_access_role[count.index].id
  policy = data.aws_iam_policy_document.secrets_access_policy.json
}

# --- Rotation Logic Policies ---
resource "aws_iam_policy" "rotation_secrets_policy" {
  name        = "rotation_secrets_policy"
  description = "Allow Lambda to read/write ONLY the hashing secret"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "ManageSecretBits",
        Effect = "Allow",
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage",
          "secretsmanager:GetSecretValue"
        ],
        Resource = module.secrets_manager.aws_hashing_secret_arn
      },
      {
        Sid    = "AllowKMSKeyUsage",
        Effect = "Allow",
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ],
        Resource = module.secrets_manager.kms_key_arn
      },
      {
        Sid    = "BasicLogging",
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = [
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.create_secret_lambda.function_name}:*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.promote_secret_lambda.function_name}:*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_rotation_secrets" {
  role       = aws_iam_role.rotation_lambda_role.name
  policy_arn = aws_iam_policy.rotation_secrets_policy.arn
}

resource "aws_iam_policy" "rotation_sfn_policy" {
  name = "rotation_sfn_policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = "lambda:InvokeFunction",
        Resource = [
          aws_lambda_function.create_secret_lambda.arn,
          aws_lambda_function.promote_secret_lambda.arn
        ]
      },
      {
        Effect   = "Allow",
        Action   = "sns:Publish",
        Resource = aws_sns_topic.secret_rotation.arn
      },
      {
        Effect = "Allow",
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ],
        Resource = module.secrets_manager.rotation_sns_key_arn
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_rotation_sfn" {
  role       = aws_iam_role.rotation_sfn_role.name
  policy_arn = aws_iam_policy.rotation_sfn_policy.arn
}
