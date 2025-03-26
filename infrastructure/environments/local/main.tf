terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  access_key                  = "test"
  secret_key                  = "test"
  region                      = "eu-west-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    apigateway = "http://localhost:4566"
    dynamodb   = "http://localhost:4566"
    iam        = "http://localhost:4566"
    lambda     = "http://localhost:4566"
    s3         = "http://localhost:4566"
  }
}

module "s3" {
  source            = "../../modules/s3"
  environment       = "local"
  bucket_name       = "truststore"
  enable_versioning = false
}

module "dynamodb" {
  source      = "../../modules/dynamodb"
  environment = "local"
  table_name  = "eligibility-signposting-data"
  hash_key    = "id"
}

module "iam" {
  source       = "../../modules/iam"
  environment  = "local"
  dynamodb_arn = module.dynamodb.table_arn
}

module "lambda" {
  source        = "../../modules/lambda"
  role_arn      = module.iam.lambda_role_arn
  environment   = "local"
  function_name = "processor"
  handler       = "index.handler"
  runtime       = "python3.9"
  source_file   = "${abspath(path.root)}/../../../dist/lambda.zip"
  s3_bucket_arn = module.s3.bucket_arn
  dynamodb_arn  = module.dynamodb.table_arn
}

resource "null_resource" "lambda_zip_check" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      test -f ${abspath(path.root)}/../../../dist/lambda.zip || \
      (echo "Missing lambda.zip in dist directory"; exit 1)
    EOT
  }
}
