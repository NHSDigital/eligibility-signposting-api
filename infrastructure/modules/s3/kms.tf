resource "aws_kms_key" "storage_bucket_cmk" {
  #checkov:skip=CKV2_AWS_64: KMS key policy is defined in api-layer iam_policies.tf
  description             = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.bucket_name} Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true

  depends_on = [
    aws_s3_bucket.storage_bucket
  ]

}

resource "aws_kms_alias" "storage_bucket_cmk" {
  name          = "alias/${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.bucket_name}-cmk"
  target_key_id = aws_kms_key.storage_bucket_cmk.key_id
}
