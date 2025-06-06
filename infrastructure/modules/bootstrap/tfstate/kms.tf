resource "aws_kms_key" "terraform_state_bucket_cmk" {
  description             = "Terraform State Bucket Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true
  tags                    = var.tags
}

resource "aws_kms_alias" "terraform_state_bucket_cmk" {
  name          = "alias/${var.project_name}-tfstate_bucket_cmk"
  target_key_id = aws_kms_key.terraform_state_bucket_cmk.key_id
}

resource "aws_kms_key_policy" "terraform_state_bucket_cmk" {
  key_id = aws_kms_key.terraform_state_bucket_cmk.id
  policy = data.aws_iam_policy_document.terraform_state_bucket_cmk.json
}

data "aws_iam_policy_document" "terraform_state_bucket_cmk" {
  statement {
    sid    = "Enable IAM User Permissions for s3 buckets"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = [aws_kms_key.terraform_state_bucket_cmk.arn]
  }
}
