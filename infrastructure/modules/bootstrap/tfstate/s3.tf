# Main state bucket
resource "aws_s3_bucket" "tfstate_bucket" {
  bucket = "${var.project_name}-${var.environment}-tfstate"
  tags = {
    Stack = "Bootstrap"
  }
}

# Enable versioning for disaster recovery
resource "aws_s3_bucket_versioning" "tfstate_bucket_versioning_config" {
  bucket = aws_s3_bucket.tfstate_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}
# Block public access to the bucket
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Encrypt the bucket with a KMS key
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate_bucket_server_side_encryption_config" {
  bucket = aws_s3_bucket.tfstate_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.terraform_state_bucket_cmk.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_policy" "tfstate_bucket" {
  bucket = aws_s3_bucket.tfstate_bucket.id
  policy = data.aws_iam_policy_document.tfstate_s3_bucket_policy.json
}

data "aws_iam_policy_document" "tfstate_s3_bucket_policy" {
  statement {
    sid = "AllowSslRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      aws_s3_bucket.tfstate_bucket.arn,
      "${aws_s3_bucket.tfstate_bucket.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test = "Bool"
      values = [
        "false",
      ]

      variable = "aws:SecureTransport"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "tfstate_bucket" {
  bucket = aws_s3_bucket.tfstate_bucket.id

  rule {
    id     = "TfStateBucketExpirationTransferToIa"
    status = "Enabled"
    filter {
      prefix = ""
    }

    expiration {
      days = 90
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Logging

resource "aws_s3_bucket" "tfstate_s3_access_logs" {
  bucket = "${var.project_name}-${var.environment}-tfstate-access-logs"
}

resource "aws_s3_bucket_logging" "s3_logging_config" {
  bucket        = aws_s3_bucket.tfstate_bucket.id
  target_bucket = aws_s3_bucket.tfstate_s3_access_logs.bucket
  target_prefix = "bucket_logs/"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate_s3_access_logs_server_side_encryption_config" {
  bucket = aws_s3_bucket.tfstate_s3_access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "tfstate_s3_access_logs_object_expiry_lifecycle_rule_config" {
  bucket = aws_s3_bucket.tfstate_s3_access_logs.id

  rule {
    id     = "StateBucketLogsExpiration"
    status = "Enabled"
    filter {
      prefix = ""
    }
    expiration {
      days = var.log_retention_in_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.log_retention_in_days
    }
  }
}

resource "aws_s3_bucket_public_access_block" "s3logs" {
  bucket = aws_s3_bucket.tfstate_s3_access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "tfstate_s3_access_logs_bucket_policy" {
  bucket = aws_s3_bucket.tfstate_s3_access_logs.id
  policy = data.aws_iam_policy_document.tfstate_s3_access_logs_bucket_policy.json
}

data "aws_iam_policy_document" "tfstate_s3_access_logs_bucket_policy" {
  statement {
    sid = "AllowSSLRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      aws_s3_bucket.tfstate_s3_access_logs.arn,
      "${aws_s3_bucket.tfstate_s3_access_logs.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test = "Bool"
      values = [
        "false",
      ]

      variable = "aws:SecureTransport"
    }
  }
}
