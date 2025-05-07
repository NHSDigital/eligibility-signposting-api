resource "aws_kms_key" "lambda_cmk" {
  description             = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.lambda_func_name} Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true
  tags                    = var.tags
}

resource "aws_kms_alias" "lambda_cmk" {
  name          = "alias/${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.lambda_func_name}-cmk"
  target_key_id = aws_kms_key.lambda_cmk.key_id
}
