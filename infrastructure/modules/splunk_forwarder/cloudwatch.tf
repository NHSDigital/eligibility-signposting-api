resource "aws_cloudwatch_event_rule" "alarm_state_change" {
  name        = "cloudwatch-alarm-state-change"
  description = "Forward CloudWatch alarm state changes to Splunk via Firehose"
  event_pattern = jsonencode({
    "source": ["aws.cloudwatch"],
    "detail-type": ["CloudWatch Alarm State Change"]
  })
}
