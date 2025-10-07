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

variable "eligibility_lambda_role_arn" {
  description = "iam role of eligibility lambda"
  type        = any
}




