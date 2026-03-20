resource "aws_cloudtrail" "data_events_trail" {
  name                          = "${var.project_name}-${var.environment}-data-events-trail"
  s3_bucket_name                = module.s3_cloudtrail_bucket.storage_bucket_name
  kms_key_id                    = aws_kms_key.cloudtrail_kms_key.arn
  include_global_service_events = true
  is_multi_region_trail         = false
  enable_log_file_validation    = true

  cloud_watch_logs_role_arn  = aws_iam_role.cloudtrail_cloudwatch_role.arn
  cloud_watch_logs_group_arn = "${aws_cloudwatch_log_group.cloudtrail_log_group.arn}:*"

  event_selector {
    read_write_type           = "ReadOnly"
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
  name          = "alias/${terraform.workspace == "default" ? "" : "${terraform.workspace}"}-cloudtrail-cmk"
  target_key_id = aws_kms_key.cloudtrail_kms_key.key_id
}

