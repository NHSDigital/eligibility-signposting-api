variable "workspace" {
  description = "Usually the developer short code or the name of the environment."
  type        = string
}

variable "eligibility_lambda_role_arn" {
  description = "lambda read role arn for dynamodb"
  type        = string
}

variable "lambda_func_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "vpc_intra_subnets" {
  description = "vpc private subnets for lambda"
  type        = list(string)
}

variable "security_group_ids" {
  description = "security groups for lambda"
  type        = list(string)
}
