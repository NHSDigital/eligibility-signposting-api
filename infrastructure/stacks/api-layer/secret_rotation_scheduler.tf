resource "aws_cloudwatch_event_rule" "rotation_schedule" {
  name        = "secret-rotation-quarterly"
  description = "Triggers rotation on the 1st day of every 3rd month"

  # Run at 08:00 UTC, on the 1st day of the month, every 3 months (Jan, Apr, Jul, Oct)
  schedule_expression = "cron(0 8 1 */3 ? *)"
}

resource "aws_cloudwatch_event_target" "rotation_target" {
  rule      = aws_cloudwatch_event_rule.rotation_schedule.name
  target_id = "RotateSecretStepFunction"
  arn       = aws_sfn_state_machine.rotation_machine.arn
  role_arn  = aws_iam_role.eventbridge_sfn_invoke_role.arn
}
