# Policy document for Permissions boundary
data "aws_iam_policy_document" "assumed_role_permissions_boundary" {
  #checkov:skip=CKV2_AWS_40: Ensure AWS IAM policy does not allow full IAM privileges
  statement {
    sid    = "RestrictRegion"
    effect = "Allow"

    actions = [
      # DynamoDB - table operations for Lambda and external write roles
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:BatchWriteItem",

      # S3 - bucket and object operations for Lambda, Firehose and External Role
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject",
      "s3:PutObjectAcl",
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:ListBucketMultipartUploads",
      "s3:GetObjectTagging",
      "s3:PutObjectTagging",
      "s3:ListBucketVersions",
      "s3:GetObjectVersion",

      # KMS - encryption/decryption for DynamoDB and S3
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",

      # CloudWatch Logs - Lambda execution and Firehose logging
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",

      # EC2 - VPC access for Lambda (from AWSLambdaVPCAccessExecutionRole)
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface",
      "ec2:AttachNetworkInterface",
      "ec2:DetachNetworkInterface",

      # Kinesis Firehose - Lambda writing audit data
      "firehose:PutRecord",
      "firehose:PutRecordBatch",

      # X-Ray - Lambda tracing
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords"
    ]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.default_aws_region]
    }
  }

  statement {
    sid       = "DenyPrivEsculationViaIamRoles"
    effect    = "Deny"
    actions   = ["iam:*"]
    resources = ["*"]
    condition {
      test     = "ArnLike"
      variable = "iam:PolicyARN"
      values   = ["arn:aws:iam::*:policy/${upper(var.project_name)}-*"]
    }
  }

  statement {
    sid       = "DenyPrivEsculationViaIamProfiles"
    effect    = "Deny"
    actions   = ["iam:*"]
    resources = ["arn:aws:iam::*:role/${upper(var.project_name)}-*"]
  }
}

# Permissions Boundary policy
resource "aws_iam_policy" "assumed_role_permissions_boundary" {
  name        = "${local.stack_name}-${upper(var.project_name)}-PermissionsBoundary"
  description = "Allows access to AWS services in the regions the client uses only"
  policy      = data.aws_iam_policy_document.assumed_role_permissions_boundary.json

  tags = merge(
    local.tags,
    {
      Stack = "api-layer"
    }
  )
}
