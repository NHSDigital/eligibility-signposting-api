module "iam_permissions_boundary" {
  source = "../iams-developer-roles"
}

# Trust policy for Lambda read role
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
      identifiers = [local.selected_arn_role]
    }
  }
}

# Lambda read role
resource "aws_iam_role" "lambda_read_role" {
  name                 = "lambda-read-role"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role.json
  permissions_boundary = module.iam_permissions_boundary.permissions_boundary_arn
}

# External write role
resource "aws_iam_role" "write_access_role" {
  name                 = "external-write-role"
  assume_role_policy   = data.aws_iam_policy_document.dps_assume_role.json
  permissions_boundary = module.iam_permissions_boundary.permissions_boundary_arn
}
