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

