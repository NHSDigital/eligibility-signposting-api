

# Lambda trust policy
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Trust policy for external write access to DPS
data "aws_iam_policy_document" "dps_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = [local.selected_role_arn]
    }
  }
}

# Trust policy kinesis firehose
data "aws_iam_policy_document" "firehose_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "splunk_firehose_assume_role" {
  name = "splunk-firehose-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "firehose.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
  tags = {
    Environment = var.environment
    Purpose     = "firehose-service-role"
    ManagedBy   = "terraform"
  }
}

# Note: EventBridge IAM roles are defined in eventbridge.tf for proper separation of concerns

resource "aws_iam_role" "eligibility_lambda_role" {
  name                 = "eligibility_lambda-role${terraform.workspace == "default" ? "" : "-${terraform.workspace}"}"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role.json
  permissions_boundary = aws_iam_policy.assumed_role_permissions_boundary.arn
}


resource "aws_iam_role" "write_access_role" {
  count                = terraform.workspace == "default" ? 1 : 0
  name                 = "eligibility-signposting-api-${local.environment}-external-write-role"
  assume_role_policy   = data.aws_iam_policy_document.dps_assume_role.json
  permissions_boundary = aws_iam_policy.assumed_role_permissions_boundary.arn
}

resource "aws_iam_role" "eligibility_audit_firehose_role" {
  name                 = "eligibility_audit_firehose-role${terraform.workspace == "default" ? "" : "-${terraform.workspace}"}"
  assume_role_policy   = data.aws_iam_policy_document.firehose_assume_role.json
  permissions_boundary = aws_iam_policy.assumed_role_permissions_boundary.arn
}

# --- Secret Rotation Roles ---
resource "aws_iam_role" "rotation_lambda_role" {
  name = "secret_rotation_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role" "rotation_sfn_role" {
  name = "secret_rotation_workflow_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = { Service = "states.amazonaws.com" }
    }]
  })
}

# -----------------------------------------------------------------------------
# IAM Role: Allow EventBridge to Start the Step Function
# -----------------------------------------------------------------------------

resource "aws_iam_role" "eventbridge_sfn_invoke_role" {
  name = "eventbridge_invoke_sfn_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = { Service = "events.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_policy" "eventbridge_sfn_policy" {
  name = "eventbridge_sfn_start_policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "states:StartExecution"
        Resource = aws_sfn_state_machine.rotation_machine.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_eb_sfn" {
  role       = aws_iam_role.eventbridge_sfn_invoke_role.name
  policy_arn = aws_iam_policy.eventbridge_sfn_policy.arn
}
