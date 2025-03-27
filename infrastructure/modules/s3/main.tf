resource "aws_s3_bucket" "main" {
  bucket = "${var.bucket_name}-${var.environment}"
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

variable "bucket_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "enable_versioning" {
  type    = bool
  default = true
}

output "bucket_arn" {
  value = aws_s3_bucket.main.arn
}
