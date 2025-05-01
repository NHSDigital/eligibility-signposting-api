variable "bucket_name" {
  description = "Name of the storage bucket"
  type        = string
}

variable "project_name" {
  default = "eligibility-signposting-api"
  type    = string
}

variable "environment" {
  description = "The purpose of the account dev/test/ref/prod or the workspace"
  type        = string
}

variable "bucket_expiration_days" {
  default     = 90
  description = "How long to keep bucket contents before expiring"
  type        = number
}

variable "log_retention_in_days" {
  default     = 5
  description = "How long to keep log bucket contents before expiring"
  type        = number
}
