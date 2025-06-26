output "firehose_stream_name" {
  value = aws_kinesis_firehose_delivery_stream.eligibility_audit_firehose_delivery_stream.name
}

output "kinesis_firehose_kms_key_arn" {
  value = aws_kms_key.firehose_key.arn
}

output "kinesis_firehose_kms_key_id" {
  value = aws_kms_key.firehose_key.id
}
