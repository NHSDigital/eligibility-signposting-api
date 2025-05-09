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


resource "aws_iam_role" "eligibility_lambda_role" {
  name                 = "eligibility_lambda-role"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role.json
  permissions_boundary = module.iam_permissions_boundary.permissions_boundary_arn
}


resource "aws_iam_role" "write_access_role" {
  name                 = "external-write-role"
  assume_role_policy   = data.aws_iam_policy_document.dps_assume_role.json
  permissions_boundary = module.iam_permissions_boundary.permissions_boundary_arn
}
