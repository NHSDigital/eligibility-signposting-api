output "firehose_stream_name" {
  value = aws_kinesis_firehose_delivery_stream.eligibility_audit_firehose_delivery_stream.name
}
