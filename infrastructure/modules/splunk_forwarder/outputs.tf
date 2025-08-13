# Output the Firehose delivery stream ARN for use by EventBridge
output "firehose_delivery_stream_arn" {
  description = "ARN of the Kinesis Firehose delivery stream for Splunk"
  value       = aws_kinesis_firehose_delivery_stream.splunk_delivery_stream.arn
}

# Output the KMS key ARN for reference
output "firehose_kms_key_arn" {
  description = "ARN of the KMS key used for Firehose encryption"
  value       = aws_kms_key.firehose_splunk_cmk.arn
}
