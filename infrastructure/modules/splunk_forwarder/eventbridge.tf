resource "aws_cloudwatch_event_target" "alarm_to_splunk" {
  rule      = aws_cloudwatch_event_rule.alarm_state_change.name
  arn       = aws_kinesis_firehose_delivery_stream.splunk_delivery_stream.arn
  role_arn  = aws_iam_role.eventbridge_to_firehose.arn
}
