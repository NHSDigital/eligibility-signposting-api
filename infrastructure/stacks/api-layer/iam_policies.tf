# Read-only policy for DynamoDB
data "aws_iam_policy_document" "dynamodb_read_policy" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    resources = [module.eligibility_status_table.arn]
  }
}

# Write-only policy for DynamoDB
data "aws_iam_policy_document" "dynamodb_write_policy" {
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
    resources = [module.eligibility_status_table.arn]
  }
}

resource "aws_iam_role_policy" "lambda_read_policy" {
  name   = "DynamoDBReadAccess"
  role   = aws_iam_role.lambda_read_role.id
  policy = data.aws_iam_policy_document.dynamodb_read_policy.json
}

resource "aws_iam_role_policy" "external_write_policy" {
  name   = "DynamoDBWriteAccess"
  role   = aws_iam_role.write_access_role.id
  policy = data.aws_iam_policy_document.dynamodb_write_policy.json
}
