# KMS CMK to encrypt/decrypt secrets
resource "aws_kms_key" "secrets_cmk" {
  #checkov:skip=CKV_AWS_111: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_356: Root user needs full KMS key management
  #checkov:skip=CKV_AWS_109: Root user needs full KMS key management
  description             = "CMK for Secrets Manager - ${var.project_name}-${var.environment}"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Allow your account root full control
      {
        Sid    = "AllowAccountAdminsFullAccess"
        Effect = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        actions = ["kms:*"]
        resources = ["*"]
      },
      # Allow Secrets Manager service to use the key
      {
        Sid    = "AllowSecretsManagerServiceUse"
        Effect = "Allow"
        Principal = { Service = "secretsmanager.amazonaws.com" }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      # Allow external role to decrypt for reading the secret
      {
        Sid    = "AllowExternalRoleDecrypt"
        Effect = "Allow"
        Principal = { AWS = var.external_write_access_role_arn }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      # Allow Lambda role to decrypt for reading the secret
      {
        Sid    = "AllowLambdaRoleDecrypt"
        Effect = "Allow"
        Principal = { AWS = var.eligibility_lambda_role_arn }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
  tags = var.tags
}
