output "firehose_stream_name" {
  value = aws_kinesis_firehose_delivery_stream.eligibility_audit_firehose_delivery_stream.name
}

output "kinesis_firehose_cmk_arn" {
  value = aws_kms_key.firehose_cmk.arn
}

output "kinesis_firehose_cmk" {
  value = aws_kms_key.firehose_cmk
}

output "kinesis_firehose_key_policy" {
  value = aws_kms_key_policy.firehose_key_policy
}
