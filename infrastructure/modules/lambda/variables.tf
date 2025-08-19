variable "eligibility_lambda_role_arn" {
  description = "lambda role arn"
  type        = string
}

variable "eligibility_lambda_role_name" {
  description = "lambda role name"
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

variable "kinesis_audit_stream_to_s3_name" {
  description = "kinesis audit stream to s3 name"
  type        = string
}

variable "log_level" {
  description = "log level"
  type        = string
}

variable "enable_xray_patching"{
  description = "flag to enable xray tracing, which puts an entry for dynamodb, s3 and firehose in trace map"
  type        = string
}

variable "provisioned_concurrency_count" {
  description = "Number of prewarmed Lambda instances"
  type        = number
}
