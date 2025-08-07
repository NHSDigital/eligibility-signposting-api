# KMS Key for Firehose encryption
resource "aws_kms_key" "firehose_splunk_cmk" {
  description             = "KMS key for encrypting Kinesis Firehose delivery stream data"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags = {
    Name      = "firehose-splunk-cmk"
    Purpose   = "Firehose encryption"
    ManagedBy = "terraform"
  }
}

# KMS Key Alias for easier identification
resource "aws_kms_alias" "firehose_splunk_cmk_alias" {
  name          = "alias/firehose-splunk-cmk"
  target_key_id = aws_kms_key.firehose_splunk_cmk.key_id
}

# KMS Key Policy for Firehose

resource "aws_kinesis_firehose_delivery_stream" "splunk_delivery_stream" {
  name        = "splunk-alarm-events"
  destination = "splunk"
  server_side_encryption {
    enabled  = true
    key_type = "CUSTOMER_MANAGED_CMK"
    key_arn  = aws_kms_key.firehose_splunk_cmk.arn
  }
  # VPC configuration is only supported for HTTP endpoint destinations in Kinesis Firehose
  # For Splunk destinations, the service runs in AWS-managed VPC but you can control network access
  # via the subnets where EventBridge (the source) runs and IAM policies

  splunk_configuration {
    hec_endpoint      = var.splunk_hec_endpoint
    hec_token         = var.splunk_hec_token
    hec_endpoint_type = "Event"
    s3_backup_mode    = "FailedEventsOnly"

    s3_configuration {
      role_arn           = var.splunk_firehose_s3_role_arn
      bucket_arn         = var.splunk_firehose_s3_backup_arn
      buffering_size     = 10
      buffering_interval = 400
      compression_format = "GZIP"
    }
  }
}
