resource "aws_kms_key" "storage_bucket_cmk" {
  description             = "${var.bucket_name} Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true
}

resource "aws_kms_alias" "storage_bucket_cmk" {
  name          = "alias/${var.project_name}-${var.bucket_name}-cmk"
  target_key_id = aws_kms_key.storage_bucket_cmk.key_id
}
