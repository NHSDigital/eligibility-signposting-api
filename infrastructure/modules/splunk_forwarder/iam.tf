resource "aws_iam_role" "eventbridge_to_firehose" {
  name = "eventbridge-to-firehose-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "events.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_to_firehose_policy" {
  role = aws_iam_role.eventbridge_to_firehose.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "firehose:PutRecord",
        "firehose:PutRecordBatch"
      ],
      Resource = aws_kinesis_firehose_delivery_stream.splunk_delivery_stream.arn
    }]
  })
}
