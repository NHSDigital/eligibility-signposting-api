resource "aws_kms_key" "flow_logs_cmk" {
  description = "KMS key for VPC Flow Logs CloudWatch Log Group"
  enable_key_rotation = true

  tags = {
    Name  = "vpc-flow-logs-kms"
    Stack = local.stack_name
  }
}

resource "aws_kms_key_policy" "flow_logs_cmk" {
  key_id = aws_kms_key.flow_logs_cmk.id
  policy = data.aws_iam_policy_document.flow_logs_cmk.json
}

data "aws_iam_policy_document" "flow_logs_cmk" {
  statement {
    sid    = "Enable IAM User Permissions for flow logs KMS key"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = [aws_kms_key.flow_logs_cmk.arn]
  }

  statement {
    sid    = "Allow CloudWatch Logs to use the key"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["logs.${local.region}.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    resources = [aws_kms_key.flow_logs_cmk.arn]
    condition {
      test     = "ArnEquals"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = [
        "arn:aws:logs:${local.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/vpc/${aws_vpc.main.id}/flow-logs"
      ]
    }
  }
}
