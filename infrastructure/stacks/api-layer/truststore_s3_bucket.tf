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
  acl     = "private"

  depends_on = [module.s3_truststore_bucket.storage_bucket_versioning_config]
}


resource "aws_kms_key_policy" "storage_bucket_cmk" {
  key_id = module.s3_truststore_bucket.storage_bucket_kms_key_id
  policy = data.aws_iam_policy_document.trust_store_kms_policy.json
}

data "aws_iam_policy_document" "trust_store_kms_policy" {
  # 1. Retain admin control
  statement {
    sid = "AllowRootAccountFullAccess"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      ]
    }

    actions   = ["kms:*"]
    resources = ["*"]
  }

  # 2. Allow API Gateway to decrypt truststore
  statement {
    sid    = "APIGatewayS3TruststoreDecrypt"
    effect = "Allow"
    principals {
      type = "Service"
      identifiers = [
        "apigateway.amazonaws.com",
        "apigateway.${var.default_aws_region}.amazonaws.com"
      ]
    }
    actions = ["kms:Decrypt"]
    resources = [module.eligibility_signposting_api_gateway.kms_key_arn]
    condition {
      test     = "StringEquals"
      variable = "kms:EncryptionContext:aws:s3:arn"
      values = [
        "${module.s3_truststore_bucket.storage_bucket_arn}/truststore.pem"
      ]
    }
  }
}

