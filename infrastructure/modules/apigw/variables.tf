variable "api_name" {
  type        = string
  description = "Name of the API Gateway"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g., local, dev, staging, prod)"
  validation {
    condition     = contains(["local", "dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: local, dev, staging, prod."
  }
}

variable "lambda_arn" {
  type        = string
  description = "ARN of the Lambda function to integrate with API Gateway"
  validation {
    condition     = can(regex("^arn:aws:lambda:", var.lambda_arn))
    error_message = "Lambda ARN must be a valid AWS Lambda ARN."
  }
}

variable "stage_name" {
  type        = string
  description = "Name of the API Gateway stage"
  default     = "v1"
}
