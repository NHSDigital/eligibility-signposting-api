resource "aws_kms_key" "splunk_hec_kms" {
  description             = "KMS key for encrypting Splunk HEC SSM parameters"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags = {
    Name        = "splunk-hec-ssm-kms-key"
    Environment = var.environment
    Stack       = local.stack_name
    Purpose     = "Splunk HEC SSM encryption"
    ManagedBy   = "terraform"
  }
}

resource "aws_kms_key_policy" "splunk_hec_kms_policy" {
  key_id = aws_kms_key.splunk_hec_kms.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowRootAccountFullAccess"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AllowSSMServiceUseOfKey"
        Effect    = "Allow"
        Principal = { Service = "ssm.amazonaws.com" }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid       = "AllowFirehoseServiceUseOfKey"
        Effect    = "Allow"
        Principal = { Service = "firehose.amazonaws.com" }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_ssm_parameter" "splunk_hec_token" {
  name        = "/splunk/hec/token"
  description = "Splunk HEC token"
  type        = "SecureString"
  key_id      = aws_kms_key.splunk_hec_kms.id # Will migrate to customer key after initial creation
  value       = var.splunk_hec_token
  tier        = "Advanced"

  tags = {
    Environment = var.environment
    Stack       = local.stack_name
    Purpose     = "Splunk HEC token"
    ManagedBy   = "terraform"
  }

  lifecycle {
    ignore_changes = [value] # Needs manual changes in future
  }
}

resource "aws_ssm_parameter" "splunk_hec_endpoint" {
  name        = "/splunk/hec/endpoint"
  description = "Splunk HEC endpoint"
  type        = "SecureString"
  key_id      = aws_kms_key.splunk_hec_kms.id
  value       = var.splunk_hec_endpoint
  tier        = "Advanced"

  tags = {
    Environment = var.environment
    Stack       = local.stack_name
    Purpose     = "Splunk HEC endpoint"
    ManagedBy   = "terraform"
  }

  lifecycle {
    ignore_changes = [value]
  }
}
