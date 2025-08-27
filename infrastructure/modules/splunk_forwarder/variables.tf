variable "splunk_hec_endpoint" {
  description = "Splunk HEC endpoint URL"
  type        = string
}

variable "splunk_hec_token" {
  description = "Splunk HEC token"
  type        = string
}

variable "splunk_firehose_s3_backup_arn" {
  description = "s3 bucket ARN for Firehose backups"
  type        = string
}

variable "splunk_firehose_s3_role_arn" {
  description = "IAM role ARN for Firehose to access S3"
  type        = string
}
