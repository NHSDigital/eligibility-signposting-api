resource "aws_kms_key" "kinesis_data_stream_kms_key" {
  description             = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"} kinesis_data_stream_kms Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true
}

resource "aws_kms_alias" "kinesis_data_stream_kms_key" {
  name          = "alias/${var.project_name}-${var.environment}-kinesis-audit-stream"
  target_key_id = aws_kms_key.kinesis_data_stream_kms_key.key_id
}


data "aws_iam_policy_document" "kinesis_stream_kms_key_policy" {
  statement {
    sid    = "EnableRootPermissions"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLambdaUseOfKey"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.eligibility_lambda_role.arn]
    }

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AllowFirehoseRoleUseOfKey"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.eligibility_audit_firehose_role.arn]
    }

    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]

    resources = ["*"]
  }
}

resource "aws_kms_key_policy" "kinesis_stream_kms_key_policy" {
  key_id = aws_kms_key.kinesis_data_stream_kms_key.id
  policy = data.aws_iam_policy_document.kinesis_stream_kms_key_policy.json
}

resource "aws_kinesis_stream" "kinesis_source_stream" {
  name             = "${var.project_name}-${var.environment}-kinesis-audit-stream"
  retention_period = 24

  stream_mode_details {
    stream_mode = "ON_DEMAND" # can discuss later
  }

  encryption_type = "KMS"
  kms_key_id      = aws_kms_key.kinesis_data_stream_kms_key.arn
}
