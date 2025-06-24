# s3
# Define bucket
resource "aws_s3_bucket" "storage_bucket" {
  #checkov:skip=CKV_AWS_144: We don't want to replicate outside our region
  #checkov:skip=CKV2_AWS_62: We won't enable event notifications for this bucket, yet
  bucket = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.project_name}-${var.environment}-${var.bucket_name}"
}

# Enable versioning for disaster recovery
resource "aws_s3_bucket_versioning" "storage_bucket_versioning_config" {
  bucket = aws_s3_bucket.storage_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ensure only secure transport is allowed

resource "aws_s3_bucket_policy" "tfstate_bucket" {
  bucket = aws_s3_bucket.storage_bucket.id
  policy = data.aws_iam_policy_document.storage_s3_bucket_policy.json
}

data "aws_iam_policy_document" "storage_s3_bucket_policy" {
  statement {
    sid = "AllowSslRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      aws_s3_bucket.storage_bucket.arn,
      "${aws_s3_bucket.storage_bucket.arn}/*",
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

# Block public access to the bucket
resource "aws_s3_bucket_public_access_block" "storage_bucket_block_public_access" {
  bucket = aws_s3_bucket.storage_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Encrypt the bucket with a KMS key
resource "aws_s3_bucket_server_side_encryption_configuration" "storage_bucket_server_side_encryption_config" {
  bucket = aws_s3_bucket.storage_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.storage_bucket_cmk.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

#Lifecycle config
resource "aws_s3_bucket_lifecycle_configuration" "storage_bucket" {
  bucket = aws_s3_bucket.storage_bucket.id

  rule {
    id     = "StorageBucketExpirationTransferToIa"
    status = "Enabled"
    filter {
      prefix = ""
    }

    expiration {
      days = var.bucket_expiration_days
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

#same again for logging buckets
resource "aws_s3_bucket" "storage_bucket_access_logs" {
  #checkov:skip=CKV_AWS_144: We don't want to replicate outside our region
  #checkov:skip=CKV2_AWS_62: We won't enable event notifications for this bucket, yet
  #checkov:skip=CKV_AWS_21: Versioning not needed given short lifecycle of logs
  bucket = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}${var.project_name}-${var.environment}-${var.bucket_name}-access-logs"
}

resource "aws_s3_bucket_logging" "storage_bucket_logging_config" {
  bucket        = aws_s3_bucket.storage_bucket.id
  target_bucket = aws_s3_bucket.storage_bucket_access_logs.bucket
  target_prefix = "bucket_logs/"
}

resource "aws_s3_bucket_policy" "storage_bucket_access_logs" {
  bucket = aws_s3_bucket.storage_bucket_access_logs.id
  policy = data.aws_iam_policy_document.access_logs_s3_bucket_policy.json
}
data "aws_iam_policy_document" "access_logs_s3_bucket_policy" {
  statement {
    sid = "AllowSslRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      aws_s3_bucket.storage_bucket_access_logs.arn,
      "${aws_s3_bucket.storage_bucket_access_logs.arn}/*",
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

resource "aws_s3_bucket_server_side_encryption_configuration" "storage_bucket_access_logs_server_side_encryption_config" {
  bucket = aws_s3_bucket.storage_bucket_access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
      kms_master_key_id = aws_kms_key.storage_bucket_cmk.arn
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "storage_bucket_access_logs_object_expiry_lifecycle_rule_config" {
  bucket = aws_s3_bucket.storage_bucket_access_logs.id

  rule {
    id     = "StorageBucketLogsExpiration"
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
  rule {
    id     = "StorageBucketLogsMultipartUploadExpiration"
    status = "Enabled"

    filter {
      prefix = ""
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_public_access_block" "storage_bucket_access_logs_public_access_block" {
  bucket = aws_s3_bucket.storage_bucket_access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
