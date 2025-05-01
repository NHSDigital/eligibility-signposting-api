module "iam_permissions_boundary" {
  source = "../iams-developer-roles"
}

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

# Lambda read role: only created in default workspace
resource "aws_iam_role" "lambda_read_role" {
  count                = local.is_iam_owner ? 1 : 0
  name                 = "lambda-read-role"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role.json
  permissions_boundary = module.iam_permissions_boundary.permissions_boundary_arn
}

# External write role: only created in default workspace
resource "aws_iam_role" "write_access_role" {
  count                = local.is_iam_owner ? 1 : 0
  name                 = "external-write-role"
  assume_role_policy   = data.aws_iam_policy_document.dps_assume_role.json
  permissions_boundary = module.iam_permissions_boundary.permissions_boundary_arn
}

# Data sources for referencing existing roles in non-default workspaces
data "aws_iam_role" "lambda_read_role" {
  count = local.is_iam_owner ? 0 : 1
  name  = "lambda-read-role"
}

data "aws_iam_role" "write_access_role" {
  count = local.is_iam_owner ? 0 : 1
  name  = "external-write-role"
}

locals {
  lambda_read_role = local.is_iam_owner ? aws_iam_role.lambda_read_role[0].id : data.aws_iam_role.lambda_read_role[0].id
  write_access_role = local.is_iam_owner ? aws_iam_role.write_access_role[0].id : data.aws_iam_role.write_access_role[0].id
}
