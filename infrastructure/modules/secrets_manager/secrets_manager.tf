# Secret definition in your account
resource "aws_secretsmanager_secret" "hashing_secret" {
  #checkov:skip=CKV2_AWS_57: Secret rotations are handled manually
  name        = "${var.project_name}-${var.environment}/hashing_secret"
  description = "cross account hashing secrets"
  kms_key_id  = aws_kms_key.secrets_cmk.arn
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Initial secrets
resource "aws_secretsmanager_secret_version" "hashing_secrets_test" {
  secret_id = aws_secretsmanager_secret.hashing_secret.id
  secret_string = "this_is_a_test_secret"
}

# Resource-based policy attached to the secret
resource "aws_secretsmanager_secret_policy" "hashing_secret_policy" {
  secret_arn = aws_secretsmanager_secret.hashing_secret.arn

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "CrossAccountAccess",
        Effect = "Allow",
        Principal = { AWS = var.external_write_access_role_arn },
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = "*"
      },
      {
        Sid    = "LambdaAccess",
        Effect = "Allow",
        Principal = { AWS = var.eligibility_lambda_role_arn },
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = "*"
      }
    ]
  })
}

