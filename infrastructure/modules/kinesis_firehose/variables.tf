variable "audit_firehose_delivery_stream_name" {
  description = "audit firehose delivery stream name"
  type        = string
}

variable "audit_firehose_role" {
  description = "audit firehose role"
  type        = any
}

variable "s3_audit_bucket_arn" {
  description = "s3 audit bucket arn"
  type        = string
}

variable "kinesis_cloud_watch_log_group_name" {
  description = "kinesis cloud watch log group name"
  type        = string
}

variable "kinesis_cloud_watch_log_stream" {
  description = "kinesis cloud watch log stream"
  type        = string
}

variable "eligibility_lambda_role_arn" {
  description = "iam role of eligibility lambda"
  type        = any
}




