data "aws_iam_policy_document" "permissions_boundary_preprod" {
  statement {
    sid    = "AllowPreprodDynamoDBItemOps"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
      "dynamodb:Scan",
      "dynamodb:BatchWriteItem",
      "dynamodb:Query"
    ]

    resources = ["*"]
  }
}
