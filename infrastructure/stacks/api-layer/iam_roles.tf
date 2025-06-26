

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

# Roles

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
