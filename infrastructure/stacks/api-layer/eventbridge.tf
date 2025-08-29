# IAM role for EventBridge to write to Firehose
resource "aws_iam_role" "eventbridge_firehose_role" {
  name = "${var.environment}-eventbridge-to-firehose-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = {
    Environment = var.environment
    Purpose     = "splunk-forwarding"
    ManagedBy   = "terraform"
  }
}

# IAM policy for EventBridge to access Firehose
resource "aws_iam_role_policy" "eventbridge_to_firehose_policy" {
  name = "${var.environment}-eventbridge-to-firehose-policy"
  role = aws_iam_role.eventbridge_firehose_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "firehose:PutRecord",
        "firehose:PutRecordBatch"
      ]
      Resource = module.splunk_forwarder.firehose_delivery_stream_arn
    }]
  })
}

# EventBridge rule to capture CloudWatch alarm state changes
resource "aws_cloudwatch_event_rule" "alarm_state_change" {
  name        = "cloudwatch-alarm-state-change-to-splunk"
  description = "Forward CloudWatch alarm state changes to Splunk via Firehose"

  event_pattern = jsonencode({
    source      = ["aws.cloudwatch"]
    detail-type = ["CloudWatch Alarm State Change"]
  })

  tags = {
    Environment = var.environment
    Purpose     = "splunk-forwarding"
    ManagedBy   = "terraform"
  }
}

# EventBridge target to send events to Firehose
resource "aws_cloudwatch_event_target" "firehose_target" {
  rule     = aws_cloudwatch_event_rule.alarm_state_change.name
  arn      = module.splunk_forwarder.firehose_delivery_stream_arn
  role_arn = aws_iam_role.eventbridge_firehose_role.arn

  # Transform the CloudWatch alarm event into a format suitable for Splunk
  input_transformer {
    input_paths = {
      account    = "$.account"
      region     = "$.region"
      time       = "$.time"
      alarm_name = "$.detail.alarmName"
      new_state  = "$.detail.state.value"
      old_state  = "$.detail.previousState.value"
      reason     = "$.detail.state.reason"
    }

    # Use a heredoc string so EventBridge placeholders like <time> are not JSON-escaped
    # (jsonencode would turn < and > into \u003c/\u003e, preventing substitution).
    input_template = <<TEMPLATE
{
  "time": "<time>",
  "source": "elid-${var.environment}:cloudwatch:alarm",
  "sourcetype": "aws:cloudwatch:alarm",
  "event": {
    "alarm_name": "<alarm_name>",
    "new_state": "<new_state>",
    "old_state": "<old_state>",
    "reason": "<reason>",
    "region": "<region>"
  }
}
TEMPLATE
  }
}
