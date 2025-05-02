resource "aws_kms_key" "dynamodb_cmk" {
  description             = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.table_name_suffix} Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true
}

resource "aws_kms_alias" "dynamodb_cmk" {
  name          = "alias/${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.table_name_suffix}-cmk"
  target_key_id = aws_kms_key.dynamodb_cmk.key_id
}
