# Secret definition in your account
resource "aws_secretsmanager_secret" "hashing_secret" {
  name        = "${var.project_name}-${var.environment}/hashing_secret"
  description = "cross account hashing secrets"
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Resource-based policy attached to the secret in your account
data "aws_iam_policy_document" "hashing_secret_policy" {
  statement {
    sid    = "CrossAccountAccess"
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]

    # Use * suffix because Secrets Manager appends a random suffix to secret ARNs
    resources = [
      "${aws_secretsmanager_secret.hashing_secret.arn}*"
    ]

    principals {
      type        = "AWS"
      identifiers = [
        var.external_write_access_role_arn
      ]
    }
  }
}

resource "aws_secretsmanager_secret_policy" "hashing_secret_policy" {
  secret_arn = aws_secretsmanager_secret.hashing_secret.arn
  policy     = data.aws_iam_policy_document.hashing_secret_policy.json
}

# Identity-based policy in the external account (must be applied there)
resource "aws_iam_role_policy" "secrets_manager_access" {
  name = "secrets-manager-access"
  role = var.external_write_access_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AllowSecretsManagerAccess"
        Effect   = "Allow"
        Action   = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}-${var.environment}/hashing_secret*"
      }
    ]
  })
}
