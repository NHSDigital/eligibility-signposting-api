resource "aws_sns_topic" "cli_login_topic" {
  name = "cli-login-notifications"
}

resource "aws_sns_topic_subscription" "email_targets" {
  for_each  = toset(var.OPERATOR_EMAILS)

  topic_arn = aws_sns_topic.cli_login_topic.arn
  protocol  = "email"
  endpoint  = each.value
}
