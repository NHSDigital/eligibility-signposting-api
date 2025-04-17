data "aws_iam_policy_document" "networking_ssm_key" {
  #checkov:skip=CKV_AWS_109: Ensure IAM policies does not allow permissions management / resource exposure without constraints
  #checkov:skip=CKV_AWS_111: Ensure IAM policies does not allow write access without constraints
  #checkov:skip=CKV_AWS_356: Ensure no IAM policies documents allow "*" as a statement's resource for restrictable actions
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
    sid    = "EncryptDecryptSsm"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ssm.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*"
    ]
    resources = ["*"]
  }
}

resource "aws_kms_key" "networking_ssm_key" {
  description             = "${var.environment} - KMS Key for Networking SSM Parameters"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  policy = data.aws_iam_policy_document.networking_ssm_key.json

  tags = {
    Name  = "${var.environment}-${local.stack_name}-ssm-key"
    Stack = local.stack_name
  }
}

resource "aws_kms_alias" "networking_ssm_key" {
  name          = "alias/${var.environment}-${local.stack_name}-ssm-parameters"
  target_key_id = aws_kms_key.networking_ssm_key.key_id
}
