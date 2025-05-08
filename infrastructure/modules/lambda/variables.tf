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

variable "file_name" {
  description = "path of the the zipped lambda"
  type        = string
}

variable "handler" {
  description = "lambda handler name"
  type        = string
}

variable "lambda_app_source_file" {
  description = "location of the lambda app in source code"
  type        = string
}

variable "lambda_app_zip_output_path" {
  description = "output location to put the zipped lambda app"
  type        = string
}
