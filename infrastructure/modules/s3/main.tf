resource "aws_s3_bucket" "main" {
  bucket = "${var.bucket_name}-${var.environment}"

  versioning {
    enabled = var.enable_versioning
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
