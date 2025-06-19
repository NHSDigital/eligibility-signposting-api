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

variable "file_name" {
  description = "path of the the zipped lambda"
  type        = string
}

variable "handler" {
  description = "lambda handler name"
  type        = string
}

variable "eligibility_rules_bucket_name" {
  description = "campaign config rules bucket name"
  type        = string
}

variable "eligibility_status_table_name" {
  description = "eligibility datastore table name"
  type        = string
}

variable "log_level" {
  description = "log level"
  type        = string
}
