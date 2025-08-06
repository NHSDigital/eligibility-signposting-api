resource "aws_kinesis_firehose_delivery_stream" "splunk_delivery_stream" {
  name        = "splunk-alarm-events"
  destination = "splunk"

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
