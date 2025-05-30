resource "aws_kms_key" "api_gateway" {
  description             = "${var.workspace} - KMS Key for ${var.api_gateway_name} API Gateway"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  tags = {
    Stack = var.stack_name
  }
}

resource "aws_kms_alias" "api_gateway" {
  name          = "alias/${var.workspace}-${var.api_gateway_name}-cloudwatch-logs"
  target_key_id = aws_kms_key.api_gateway.key_id
}

resource "aws_kms_key_policy" "api_gateway" {
  key_id = aws_kms_key.api_gateway.id
  policy = data.aws_iam_policy_document.api_gateway.json
}

data "aws_iam_policy_document" "api_gateway" {
  statement {
    sid    = "Enable IAM User Permissions for ${var.api_gateway_name} API Gateway"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = [aws_kms_key.api_gateway.arn]
  }
  statement {
    sid    = "APIGatewayCloudwatchKMSAccess"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["logs.${var.region}.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*"
    ]
    resources = [aws_kms_key.api_gateway.arn]
  }
}
