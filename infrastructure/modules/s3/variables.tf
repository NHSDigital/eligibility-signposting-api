variable "bucket_name" {
  description = "Name of the storage bucket"
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
