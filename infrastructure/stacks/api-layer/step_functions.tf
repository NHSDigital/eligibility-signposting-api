resource "aws_sfn_state_machine" "rotation_machine" {
  name     = "SecretRotationWorkflow"
  role_arn = aws_iam_role.rotation_sfn_role.arn

  definition = jsonencode({
    Comment = "Secret Rotation: Create -> Manual Pause -> Promote -> Manual Pause",
    StartAt = "CreatePendingVersion",
    States = {
      "CreatePendingVersion" : {
        Type     = "Task",
        Resource = aws_lambda_function.create_secret_lambda.arn,
        Next     = "WaitFor_AddNewHashes"
      },
      "WaitFor_AddNewHashes" : {
        Type           = "Task",
        Resource       = "arn:aws:states:::sns:publish.waitForTaskToken",
        TimeoutSeconds = 86400,
        Parameters = {
          TopicArn = aws_sns_topic.cli_login_topic.arn,
          Message = {
            Title         = "STEP 1 DONE: Pending Secret Created",
            Instructions  = "1. Run 'Add New Hashes' job. 2. Copy TaskToken below. 3. Run CLI resume command.",
            SecretName    = module.secrets_manager.aws_hashing_secret_name,
            "TaskToken.$" = "$$.Task.Token"
          }
        },
        Catch = [{ ErrorEquals = ["States.Timeout"], Next = "Fail_Timeout" }],
        Next  = "PromoteToCurrent"
      },
      "PromoteToCurrent" : {
        Type     = "Task",
        Resource = aws_lambda_function.promote_secret_lambda.arn,
        Next     = "WaitFor_DelOldHashes"
      },
      "WaitFor_DelOldHashes" : {
        Type           = "Task",
        Resource       = "arn:aws:states:::sns:publish.waitForTaskToken",
        TimeoutSeconds = 86400,
        Parameters = {
          TopicArn = aws_sns_topic.cli_login_topic.arn,
          Message = {
            Title         = "STEP 2 DONE: Promoted to Current",
            Instructions  = "1. Run 'Delete Old Hashes' job. 2. Copy TaskToken below. 3. Run CLI resume command.",
            SecretName    = module.secrets_manager.aws_hashing_secret_name,
            "TaskToken.$" = "$$.Task.Token"
          }
        },
        Catch = [{ ErrorEquals = ["States.Timeout"], Next = "Fail_Timeout" }],
        End   = true
      },
      "Fail_Timeout" : {
        Type  = "Fail",
        Error = "ManualActionTimedOut",
        Cause = "User did not respond within 24 hours."
      }
    }
  })
}
