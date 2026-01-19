resource "aws_sfn_state_machine" "rotation_machine" {
  name     = "SecretRotationWorkflow"
  role_arn = aws_iam_role.rotation_sfn_role.arn

  logging_configuration {
    level                  = "ALL"
    include_execution_data = true
    log_destination        = "${aws_cloudwatch_log_group.rotation_sfn_logs.arn}:*"
  }

  definition = jsonencode({
    Comment = "Secret Rotation: Create -> Manual Pause -> Promote -> Manual Pause",
    StartAt = "CreatePendingVersion",
    States  = {
      CreatePendingVersion = {
        Type     = "Task",
        Resource = aws_lambda_function.create_secret_lambda.arn,
        Catch    = [{ ErrorEquals = ["States.ALL"], Next = "NotifyFailure" }],
        Next     = "WaitFor_AddNewHashes"
      },

      WaitFor_AddNewHashes = {
        Type           = "Task",
        Resource       = "arn:aws:states:::sns:publish.waitForTaskToken",
        TimeoutSeconds = 86400,
        Parameters = {
          Subject  = "Action required: AWSPENDING secret created (Environment: ${var.environment})",
          TopicArn = aws_sns_topic.secret_rotation.arn,
          "Message.$" = "States.Format('======================================================\nAction required: AWSPENDING secret created (Environment: ${var.environment})\n======================================================\n\nA manual action is required to proceed.\n\nCONTEXT:\nSecret Name: ${module.secrets_manager.aws_hashing_secret_name}\n\nINSTRUCTIONS:\n1. Run the \"Add New Hashes (elid_add_new_salt)\" job.\n2. Ensure the new hashes are working as expected.\n3. Run the command below to approve and resume the workflow:\n\naws stepfunctions send-task-success --task-token {} --task-output {}\n\n======================================================\n', $$.Task.Token, '{}')"
        },
        Catch = [
          { ErrorEquals = ["States.Timeout"], Next = "NotifyTimeout" },
          { ErrorEquals = ["States.ALL"], Next = "NotifyFailure" }
        ],
        Next = "PromoteToCurrent"
      },

      PromoteToCurrent = {
        Type     = "Task",
        Resource = aws_lambda_function.promote_secret_lambda.arn,
        Catch    = [{ ErrorEquals = ["States.ALL"], Next = "NotifyFailure" }],
        Next     = "WaitFor_DelOldHashes"
      },

      WaitFor_DelOldHashes = {
        Type           = "Task",
        Resource       = "arn:aws:states:::sns:publish.waitForTaskToken",
        TimeoutSeconds = 86400,
        Parameters = {
          Subject  = "Action required: Secret AWSPENDING promoted to AWSCURRENT (Environment: ${var.environment})",
          TopicArn = aws_sns_topic.secret_rotation.arn,
          "Message.$" = "States.Format('======================================================\nAction required: Secret AWSPENDING promoted to AWSCURRENT (Environment: ${var.environment})\n======================================================\n\nA manual action is required to proceed.\n\nCONTEXT:\nSecret Name: ${module.secrets_manager.aws_hashing_secret_name}\n\nINSTRUCTIONS:\n1. Run the \"Delete Old Hashes (elid_delete_old_salt)\" job.\n2. Ensure the old hashes have been removed successfully.\n3. Run the command below to approve and resume the workflow:\n\naws stepfunctions send-task-success --task-token {} --task-output {}\n\n======================================================\n', $$.Task.Token, '{}')"
        },
        Catch = [
          { ErrorEquals = ["States.Timeout"], Next = "NotifyTimeout" },
          { ErrorEquals = ["States.ALL"], Next = "NotifyFailure" }
        ],
        End = true
      },

      NotifyTimeout = {
        Type     = "Task",
        Resource = "arn:aws:states:::sns:publish",
        Parameters = {
          TopicArn = aws_sns_topic.secret_rotation.arn,
          Subject  = "Warning: Secret rotation timed out (Environment: ${var.environment})",
          Message  = local.timeout_message
        },
        Next = "Fail_Timeout"
      },

      Fail_Timeout = {
        Type  = "Fail",
        Error = "ManualActionTimedOut",
        Cause = "User did not respond within 24 hours."
      },

      NotifyFailure = {
        Type     = "Task",
        Resource = "arn:aws:states:::sns:publish",
        Parameters = {
          TopicArn    = aws_sns_topic.secret_rotation.arn,
          Subject     = "Critical: Secret Rotation Failed (Environment: ${var.environment})",
          "Message.$" = local.failure_message
        },
        Next = "Fail_Generic"
      },

      Fail_Generic = {
        Type = "Fail"
      }
    }
  })
}

locals {
  failure_message = <<EOT
States.Format('
======================================================
Critical: Rotation failed (Environment: ${var.environment})
======================================================

The workflow encountered an error and could not complete.

CONTEXT:
Secret Name: ${module.secrets_manager.aws_hashing_secret_name}

ERROR DETAILS:
{}

======================================================
', $.Cause)
EOT

  timeout_message = <<EOT
======================================================
Warning: Rotation timed out (Environment: ${var.environment})
======================================================

The manual verification step was not completed within the 24-hour limit.

Secret Name: ${module.secrets_manager.aws_hashing_secret_name}
======================================================
EOT
}
