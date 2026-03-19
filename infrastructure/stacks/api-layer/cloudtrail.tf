locals {
  cloudtrail_name = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.project_name}-${var.environment}-audit-trail"
}

resource "aws_kms_key" "cloudtrail_cmk" {
  description             = "KMS key for CloudTrail log file encryption"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowCloudTrailEncryptLogs"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey*",
          "kms:DescribeKey",
          "kms:Encrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceArn" = "arn:aws:cloudtrail:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:trail/${local.cloudtrail_name}"
          }
          StringLike = {
            "kms:EncryptionContext:aws:cloudtrail:arn" = "arn:aws:cloudtrail:*:${data.aws_caller_identity.current.account_id}:trail/*"
          }
        }
      }
    ]
  })
}

resource "aws_kms_alias" "cloudtrail_cmk" {
  name          = "alias/${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.project_name}-${var.environment}-cloudtrail"
  target_key_id = aws_kms_key.cloudtrail_cmk.id
}

resource "aws_cloudwatch_log_group" "cloudtrail_logs" {
  name              = "NHSDAudit_trail_log_group"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.cloudtrail_cmk.arn
}

resource "aws_iam_role" "cloudtrail_to_cloudwatch" {
  name = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.project_name}-${var.environment}-cloudtrail-cw-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "cloudtrail_to_cloudwatch" {
  name = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.project_name}-${var.environment}-cloudtrail-cw-policy"
  role = aws_iam_role.cloudtrail_to_cloudwatch.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.cloudtrail_logs.arn}:*"
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "cloudtrail_logs_bucket" {
  bucket = module.s3_elid_cloudwatch_bucket.storage_bucket_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureTransport"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          module.s3_elid_cloudwatch_bucket.storage_bucket_arn,
          "${module.s3_elid_cloudwatch_bucket.storage_bucket_arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = module.s3_elid_cloudwatch_bucket.storage_bucket_arn
        Condition = {
          StringEquals = {
            "aws:SourceArn" = "arn:aws:cloudtrail:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:trail/${local.cloudtrail_name}"
          }
        }
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${module.s3_elid_cloudwatch_bucket.storage_bucket_arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl"   = "bucket-owner-full-control"
            "aws:SourceArn" = "arn:aws:cloudtrail:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:trail/${local.cloudtrail_name}"
          }
        }
      }
    ]
  })
}

resource "aws_cloudtrail" "api_audit_trail" {
  name                          = local.cloudtrail_name
  s3_bucket_name                = module.s3_elid_cloudwatch_bucket.storage_bucket_name
  kms_key_id                    = aws_kms_key.cloudtrail_cmk.arn
  include_global_service_events = true
  is_multi_region_trail         = false
  enable_log_file_validation    = true

  cloud_watch_logs_role_arn  = aws_iam_role.cloudtrail_to_cloudwatch.arn
  cloud_watch_logs_group_arn = "${aws_cloudwatch_log_group.cloudtrail_logs.arn}:*"

  # Keep management event coverage for security controls.
  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  # Capture DynamoDB read data events for the eligibility status table.
  event_selector {
    read_write_type           = "ReadOnly"
    include_management_events = false

    data_resource {
      type   = "AWS::DynamoDB::Table"
      values = [module.eligibility_status_table.arn]
    }
  }

  depends_on = [
    aws_s3_bucket_policy.cloudtrail_logs_bucket,
    aws_iam_role_policy.cloudtrail_to_cloudwatch
  ]
}

