resource "aws_iam_role" "lambda_exec" {
  name = "${var.environment}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Policy for DynamoDB read access
resource "aws_iam_policy" "dynamodb_read_access" {
  name        = "${var.environment}-dynamodb-read-access"
  description = "Allows Lambda to read from DynamoDB"
  policy      = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        Effect   = "Allow"
        Resource = var.dynamodb_arn
      }
    ]
  })
}

# Policy for S3 write access
resource "aws_iam_policy" "s3_write_access" {
  name        = "${var.environment}-s3-write-access"
  description = "Allows Lambda to write to S3"
  policy      = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["s3:PutObject", "s3:PutObjectAcl"]
        Effect   = "Allow"
        Resource = "${var.s3_bucket_arn}/*"
      }
    ]
  })
}

# Attach DynamoDB read policy to the Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_dynamodb_read_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.dynamodb_read_access.arn
}

# Attach S3 write policy to the Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_s3_write_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.s3_write_access.arn
}
