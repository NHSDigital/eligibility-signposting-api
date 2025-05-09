output "arn" {
  value = aws_dynamodb_table.dynamodb_table.arn
}

output "table_name" {
  value = aws_dynamodb_table.dynamodb_table.name
}

output "dynamodb_kms_key_arn" {
  value = aws_kms_key.dynamodb_cmk.arn
}

output "dynamodb_kms_key_id" {
  value = aws_kms_key.dynamodb_cmk.id
}

