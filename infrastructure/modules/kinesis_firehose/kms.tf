resource "aws_kms_key" "firehose_cmk" {
  description             = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.audit_firehose_delivery_stream_name} Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true
  tags                    = var.tags
}


resource "aws_kms_alias" "firehose_cmk" {
  name          = "alias/${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.audit_firehose_delivery_stream_name}-cmk"
  target_key_id = aws_kms_key.firehose_cmk.key_id
}

resource "aws_kms_key_policy" "firehose_key_policy" {
  key_id = aws_kms_key.firehose_cmk.id
  policy = data.aws_iam_policy_document.firehose_kms_key_policy.json
}


data "aws_iam_policy_document" "firehose_kms_key_policy" {
  #checkov:skip=CKV_AWS_111: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_356: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_109: Root user needs full KMS key management
  statement {
    sid    = "EnableIamUserPermissions"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }
  statement {
    sid    = "EnableRootUserPermissions"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowFirehoseAccess"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    resources = [aws_kms_key.firehose_cmk.arn]
  }

  statement {
    sid    = "AllowFirehoseRoleUsage"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [var.audit_firehose_role.arn]
    }
    actions   = ["kms:*"]
    resources = [aws_kms_key.firehose_cmk.arn]
  }

  statement {
    sid    = "AllowCloudWatchLogsUseOfTheKey"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["logs.${var.region}.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    resources = [aws_kms_key.firehose_cmk.arn]
    condition {
      test     = "StringEquals"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values = [
        "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/kinesisfirehose/${var.project_name}-${var.environment}-audit"
      ]
    }
  }

  statement {
    sid    = "AllowLambdaUsage"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [var.eligibility_lambda_role_arn]
    }
    actions = [
      "kms:*"
    ]
    resources = [aws_kms_key.firehose_cmk.arn]
  }
}
