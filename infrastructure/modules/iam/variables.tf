variable "environment" {
  type        = string
  description = "Deployment environment name"
}

variable "dynamodb_arn" {
  type        = string
  description = "ARN of DynamoDB table for Lambda access"
}
