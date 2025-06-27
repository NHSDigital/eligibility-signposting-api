resource "aws_kinesis_firehose_delivery_stream" "eligibility_audit_firehose_delivery_stream" {
  name        = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.project_name}-${var.environment}-${var.audit_firehose_delivery_stream_name}"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn   = var.audit_firehose_role_arn
    bucket_arn = var.s3_audit_bucket_arn

    buffering_size     = 1
    buffering_interval = 60
    compression_format = "UNCOMPRESSED"

    kms_key_arn = aws_kms_key.firehose_cmk.arn

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = var.kinesis_cloud_watch_log_group_name
      log_stream_name = var.kinesis_cloud_watch_log_stream
    }
  }

  server_side_encryption {
    enabled  = true
    key_arn  = aws_kms_key.firehose_cmk.arn
    key_type = "CUSTOMER_MANAGED_CMK"
  }

  tags = var.tags
}
