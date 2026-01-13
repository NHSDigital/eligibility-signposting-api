resource "aws_sns_topic" "secret_rotation" {
  name = "secret-rotation-notifications"
  kms_master_key_id = module.secrets_manager.rotation_sns_key_id
}

resource "aws_sns_topic_subscription" "email_targets" {
  for_each  = toset(var.OPERATOR_EMAILS)

  topic_arn = aws_sns_topic.secret_rotation.arn
  protocol  = "email"
  endpoint  = each.value
}
