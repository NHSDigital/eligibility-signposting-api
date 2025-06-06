resource "aws_dynamodb_table" "dynamodb_table" {
  name         = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.project_name}-${var.environment}-${var.table_name_suffix}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = var.partition_key

  attribute {
    name = var.partition_key
    type = var.partition_key_type
  }

  dynamic "attribute" {
    for_each = var.sort_key != null ? [1] : []
    content {
      name = var.sort_key
      type = var.sort_key_type
    }
  }

  range_key = var.sort_key != null ? var.sort_key : null

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_cmk.arn
  }

  #checkov:skip=CKV_AWS_28: Point-in-time recovery is enabled only for production environments
  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  tags = var.tags
}
