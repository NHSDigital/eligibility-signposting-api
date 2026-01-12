output "aws_hashing_secret_arn" {
  value = aws_secretsmanager_secret.hashing_secret.arn
}

output "aws_hashing_secret_name" {
  value = aws_secretsmanager_secret.hashing_secret.name
}

output "kms_key_arn" {
  value = aws_kms_key.secrets_cmk.arn
}

output "rotation_sns_key_id" {
  value = aws_kms_key.rotation_sns_cmk.key_id
}

output "rotation_sns_key_arn" {
  value = aws_kms_key.rotation_sns_cmk.arn
}
