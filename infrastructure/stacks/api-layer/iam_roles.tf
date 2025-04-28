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
data "aws_iam_policy_document" "write_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::448049830832:role/terraform-developer-role"]  #TODO: Replace with DPS AWS account ID
    }
  }
}

# Lambda read role
resource "aws_iam_role" "lambda_read_role" {
  name               = "LambdaReadRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# External write role
resource "aws_iam_role" "write_access_role" {
  name               = "ExternalWriteRole"
  assume_role_policy = data.aws_iam_policy_document.write_assume_role.json
}
