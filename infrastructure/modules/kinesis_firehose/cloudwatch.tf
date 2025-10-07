# CloudWatch Log Group for Kinesis

resource "aws_cloudwatch_log_group" "firehose_audit" {
  name              = "/aws/kinesisfirehose/${var.project_name}-${var.environment}-audit"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.firehose_cmk.arn

  tags = {
    Name  = "kinesis-firehose-logs"
    Stack = var.stack_name
  }

  depends_on = [
    aws_kms_key.firehose_cmk,
    aws_kms_key_policy.firehose_key_policy
  ]
}

resource "aws_cloudwatch_log_stream" "firehose_audit_stream" {
  name           = "audit_stream_log"
  log_group_name = aws_cloudwatch_log_group.firehose_audit.name

  depends_on = [
    aws_cloudwatch_log_group.firehose_audit
  ]
}
