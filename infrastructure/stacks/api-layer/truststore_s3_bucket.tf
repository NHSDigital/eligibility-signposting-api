module "s3_truststore_bucket" {
  source       = "../../modules/s3"
  bucket_name  = "truststore"
  environment  = var.environment
  project_name = var.project_name
  stack_name   = local.stack_name
  workspace    = terraform.workspace
}

resource "aws_s3_bucket_policy" "truststore" {
  bucket = module.s3_truststore_bucket.storage_bucket_id
  policy = data.aws_iam_policy_document.truststore_api_gateway.json
}

data "aws_iam_policy_document" "truststore_api_gateway" {
  # Deny non-SSL
  statement {
    sid    = "AllowSslRequestsOnly"
    actions = ["s3:*"]
    effect = "Deny"
    resources = [
      module.s3_truststore_bucket.storage_bucket_arn,
      "${module.s3_truststore_bucket.storage_bucket_arn}/*"
    ]
    principals {
      type = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values = ["false"]
    }
  }
  statement {
    sid    = "Enable S3 access permissions for API Gateway"
    effect = "Allow"

    principals {
      type = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }

    actions = ["s3:GetObject"]

    resources = [
      "${module.s3_truststore_bucket.storage_bucket_arn}/truststore.pem"
    ]
  }
}

resource "aws_s3_object" "pem_file" {
  bucket  = module.s3_truststore_bucket.storage_bucket_name
  key     = "truststore.pem"
  content = local.pem_file_content

  acl = "private"

  override_provider {
    default_tags {
      tags = {}
    }
  }

  # Explicitly set empty tags to override default_tags due to S3 object 10-tag limit
  tags = {}

  lifecycle {
    ignore_changes = [tags_all]
  }
}
