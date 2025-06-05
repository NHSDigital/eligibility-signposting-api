resource "aws_kms_key" "storage_bucket_cmk" {
  description             = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.bucket_name} Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true
}

resource "aws_kms_alias" "storage_bucket_cmk" {
  name          = "alias/${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.bucket_name}-cmk"
  target_key_id = aws_kms_key.storage_bucket_cmk.key_id
}

resource "aws_kms_key_policy" "storage_bucket_cmk" {
  key_id = aws_kms_key.storage_bucket_cmk.id
  policy = data.aws_iam_policy_document.storage_bucket_cmk.json
}

data "aws_iam_policy_document" "storage_bucket_cmk" {
  statement {
    sid    = "Enable IAM User Permissions for s3 buckets"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = [aws_kms_key.storage_bucket_cmk.arn]
  }
}
