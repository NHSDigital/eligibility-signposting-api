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
