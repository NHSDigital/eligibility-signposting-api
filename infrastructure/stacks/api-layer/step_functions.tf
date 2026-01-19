resource "aws_sfn_state_machine" "rotation_machine" {
  #checkov:skip=CKV_AWS_284: No x-ray needed for this resource
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
    States = {
      "CreatePendingVersion" : {
        Type     = "Task",
        Resource = aws_lambda_function.create_secret_lambda.arn,
        Catch    = [{ ErrorEquals = ["States.ALL"], Next = "NotifyFailure" }],
        Next     = "WaitFor_AddNewHashes"
      },
      "WaitFor_AddNewHashes" : {
        Type           = "Task",
        Resource       = "arn:aws:states:::sns:publish.waitForTaskToken",
        TimeoutSeconds = 86400,
        Parameters = {
          Subject     = "Action required: AWSPENDING secret created (Environment: ${var.environment})",
          TopicArn    = aws_sns_topic.secret_rotation.arn,
          "Message.$" = local.add_jobs_message
        },
        Catch = [
          { ErrorEquals = ["States.Timeout"], Next = "NotifyTimeout" },
          { ErrorEquals = ["States.ALL"], Next = "NotifyFailure" }
        ],
        Next = "PromoteToCurrent"
      },
      "PromoteToCurrent" : {
        Type     = "Task",
        Resource = aws_lambda_function.promote_secret_lambda.arn,
        Catch    = [{ ErrorEquals = ["States.ALL"], Next = "NotifyFailure" }],
        Next     = "WaitFor_DelOldHashes"
      },
      "WaitFor_DelOldHashes" : {
        Type           = "Task",
        Resource       = "arn:aws:states:::sns:publish.waitForTaskToken",
        TimeoutSeconds = 86400,
        Parameters = {
          Subject     = "Action required: Secret AWSPENDING promoted to AWSCURRENT (Environment: ${var.environment})",
          TopicArn    = aws_sns_topic.secret_rotation.arn,
          "Message.$" = local.delete_jobs_message
        },
        Catch = [
          { ErrorEquals = ["States.Timeout"], Next = "NotifyTimeout" },
          { ErrorEquals = ["States.ALL"], Next = "NotifyFailure" }
        ],
        End = true
      },

      "NotifyTimeout" : {
        Type     = "Task",
        Resource = "arn:aws:states:::sns:publish",
        Parameters = {
          TopicArn    = aws_sns_topic.secret_rotation.arn,
          Subject     = "Warning: Secret rotation timed out (Environment: ${var.environment})",
          "Message.$" = local.timeout_message
        },
        Next = "Fail_Timeout"
      },

      "Fail_Timeout" : {
        Type  = "Fail",
        Error = "ManualActionTimedOut",
        Cause = "User did not respond within 24 hours."
      },
      "NotifyFailure" : {
        Type     = "Task",
        Resource = "arn:aws:states:::sns:publish",
        Parameters = {
          TopicArn    = aws_sns_topic.secret_rotation.arn,
          Subject     = "Critical: Secret Rotation Failed (Environment: ${var.environment})",
          "Message.$" = local.failure_message
        },
        Next = "Fail_Generic"
      },
      "Fail_Generic" : {
        Type = "Fail"
      }
    }
  })
}

locals {
  add_jobs_message = <<EOT
States.Format('
======================================================
Action required: AWSPENDING secret created (Environment: ${var.environment})
======================================================

A manual action is required to proceed.

CONTEXT:
Secret Name: ${module.secrets_manager.aws_hashing_secret_name}

INSTRUCTIONS:
1. Run the "Add New Hashes (elid_add_new_salt)" job.
2. Ensure the new hashes are working as expected.
3. Run the command below to approve and resume the workflow:

aws stepfunctions send-task-success --task-token {} --task-output {{}}

======================================================
', $$.Task.Token)
EOT

  delete_jobs_message = <<EOT
States.Format('
======================================================
Action required: Secret AWSPENDING promoted to AWSCURRENT (Environment: ${var.environment})
======================================================

A manual action is required to proceed.

CONTEXT:
Secret Name: ${module.secrets_manager.aws_hashing_secret_name}

INSTRUCTIONS:
1. Run the "Delete Old Hashes (elid_delete_old_salt)" job.
2. Ensure the old hashes have been removed successfully.
3. Run the command below to approve and resume the workflow:

aws stepfunctions send-task-success --task-token {} --task-output {{}}

======================================================
', $$.Task.Token)
EOT

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

------------------------------------------------------
HOW TO FIX: "Pending Version Exists" Error
------------------------------------------------------
If the error above indicates a pending version already exists,
you must clean it up manually.

1. Find the Version ID of the pending secret:
aws secretsmanager list-secret-version-ids --secret-id ${module.secrets_manager.aws_hashing_secret_name}

2. Remove the AWSPENDING label:
aws secretsmanager update-secret-version-stage --secret-id ${module.secrets_manager.aws_hashing_secret_name} --version-stage AWSPENDING --remove-from-version-id <OLD_PENDING_VERSION_ID>

======================================================
', $.Cause)
EOT

  timeout_message = <<EOT
States.Format('
======================================================
Warning: Rotation timed out (Environment: ${var.environment})
======================================================

The manual verification step was not completed within the 24-hour limit.
The rotation workflow has been stopped.

CONTEXT:
Secret Name: ${module.secrets_manager.aws_hashing_secret_name}

IMPACT:
No immediate impact. Your applications are still using the current secret.
However, a "Pending" version may have been left behind.

ACTION REQUIRED:
Before the next rotation run, you must remove the pending version:

1. Find the Version ID:
aws secretsmanager list-secret-version-ids --secret-id ${module.secrets_manager.aws_hashing_secret_name}

2. Remove the AWSPENDING label:
aws secretsmanager update-secret-version-stage --secret-id ${module.secrets_manager.aws_hashing_secret_name} --version-stage AWSPENDING --remove-from-version-id <OLD_PENDING_VERSION_ID>

======================================================
')
EOT
}
