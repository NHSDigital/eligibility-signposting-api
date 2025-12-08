output "aws_hashing_secret_arn" {
  value = aws_secretsmanager_secret.hashing_secret.arn
}
