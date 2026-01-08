output "aws_hashing_secret_arn" {
  value = aws_secretsmanager_secret.hashing_secret.arn
}

output "aws_hashing_secret_name" {
  value = aws_secretsmanager_secret.hashing_secret.name
}

output "kms_key_arn" {
  value = aws_kms_key.secrets_cmk.arn
}
