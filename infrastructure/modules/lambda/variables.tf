variable "environment" {
  type        = string
  description = "Deployment environment name"
}

variable "function_name" {
  type        = string
  description = "Base name for Lambda function"
}

variable "handler" {
  type        = string
  description = "Lambda handler entry point"
}

variable "runtime" {
  type        = string
  description = "Lambda runtime identifier"
}

variable "source_file" {
  type        = string
  description = "Path to Lambda deployment package"

  validation {
    condition     = fileexists(var.source_file)
    error_message = "Lambda ZIP file must exist at path: ${var.source_file}"
  }
}

variable "role_arn" {
  type        = string
  description = "Execution role ARN"
}

variable "dynamodb_arn" {
  type        = string
  description = "ARN of DynamoDB table for Lambda access"
}

variable "s3_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket for Lambda access"
}
