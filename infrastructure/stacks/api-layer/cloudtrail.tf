resource "aws_cloudtrail" "data_events_trail" {
  #checkov:skip=CKV_AWS_67: Ensure CloudTrail is enabled in all Regions
  #checkov:skip=CKV_AWS_252: Ensure CloudTrail defines an SNS Topic
  name                          = "${var.project_name}-${var.environment}-data-events-trail"
  s3_bucket_name                = module.s3_cloudtrail_bucket.storage_bucket_name
  kms_key_id                    = aws_kms_key.cloudtrail_kms_key.arn
  include_global_service_events = true
  is_multi_region_trail         = false
  enable_log_file_validation    = true

  cloud_watch_logs_role_arn  = aws_iam_role.cloudtrail_cloudwatch_role.arn
  cloud_watch_logs_group_arn = "${aws_cloudwatch_log_group.cloudtrail_log_group.arn}:*"

  event_selector {
    read_write_type           = "All"
    include_management_events = false

    data_resource {
      type   = "AWS::DynamoDB::Table"
      values = [module.eligibility_status_table.arn]
    }
  }
}

resource "aws_kms_key" "cloudtrail_kms_key" {
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
      }
    ]
  })

  tags = {
    environment  = var.environment
    project_name = var.project_name
    stack_name   = local.stack_name
    workspace    = terraform.workspace
  }

}

# KMS key alias
resource "aws_kms_alias" "cloudtrail_kms_alias" {
  name          = "alias/${var.project_name}-${var.environment}-cloudtrail-cmk"
  target_key_id = aws_kms_key.cloudtrail_kms_key.key_id
}

# KMS key policy to allow CloudTrail and CloudWatch Logs to use the key for encryption and decryption
resource "aws_kms_key_policy" "cloudtrail_kms_key_policy" {
  key_id = aws_kms_key.cloudtrail_kms_key.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "logs.amazonaws.com"
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
