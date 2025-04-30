resource "aws_dynamodb_table" "dynamodb_table" {
  name         = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.table_name_suffix}"
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

  tags = var.tags
}
