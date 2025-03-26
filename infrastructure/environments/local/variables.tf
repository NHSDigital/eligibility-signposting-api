variable "bucket_name" {
  description = "Name of the S3 bucket"
}

variable "table_name" {
  description = "Name of the DynamoDB table"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}
