locals {
  rotation_schedules = {
    # PROD: Run on the 1st Tuesday of Jan, Apr, Jul, Oct at 11:00 UTC
    # Syntax breakdown:
    # ?        -> Ignore Day-of-month (required when specifying Day-of-week)
    # 1,4,7,10 -> The months (Quarterly)
    # 3#1      -> Tuesday (Day 3) -> First instance (#1)
    "prod" = "cron(0 11 ? 1,4,7,10 3#1 *)"

    # PREPROD: Run on the Last Tuesday of Dec, Mar, Jun, Sep at 11:00 UTC
    # This ensures it runs exactly 7 days before the Prod schedule.
    # 3L       -> Tuesday (Day 3) -> Last instance (L)
    "preprod" = "cron(0 11 ? 3,6,9,12 3L *)"
  }

  is_rotation_enabled = contains(keys(local.rotation_schedules), var.environment)
}

resource "aws_cloudwatch_event_rule" "rotation_schedule" {
  count = local.is_rotation_enabled ? 1 : 0
  name        = "secret-rotation-quarterly"
  description = "Triggers secret rotation (Enabled for: ${var.environment})"
  schedule_expression = local.rotation_schedules[var.environment]
}

resource "aws_cloudwatch_event_target" "rotation_target" {
  count = local.is_rotation_enabled ? 1 : 0
  rule      = aws_cloudwatch_event_rule.rotation_schedule[0].name
  target_id = "RotateSecretStepFunction"
  arn       = aws_sfn_state_machine.rotation_machine.arn
  role_arn  = aws_iam_role.eventbridge_sfn_invoke_role.arn
}
