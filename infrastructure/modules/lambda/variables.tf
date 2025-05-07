variable "workspace" {
  description = "Usually the developer short code or the name of the environment."
  type        = string
}

variable "lambda_read_role_arn" {
  description = "lambda read role arn for dynamodb"
  type    = string
}

variable "lambda_func_name" {
  description = "Name of the Lambda function"
  type    = string
}

