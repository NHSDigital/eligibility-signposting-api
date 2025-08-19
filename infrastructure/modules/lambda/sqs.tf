resource "aws_sqs_queue" "lambda_dlq" {
  name = "${var.lambda_func_name}_dead_letter_queue"
  kms_master_key_id = aws_kms_key.lambda_cmk.id
  tags = var.tags
}

# sql policy attachment
resource "aws_iam_role_policy" "lambda_sqs_send_inline" {
  name = "LambdaSQSMessageSendPolicy"
  role = var.eligibility_lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid      = "AllowSQSSendMessage",
        Effect   = "Allow",
        Action   = ["sqs:SendMessage"],
        Resource = aws_sqs_queue.lambda_dlq.arn
      }
    ]
  })
}
