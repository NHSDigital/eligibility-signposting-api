variable "workspace" {
  description = "Usually the developer short code or the name of the environment."
  type        = string
}

variable "project_name" {
  default = "eligibility-signposting-api"
  type    = string
}

variable "table_name_suffix" {
  description = "Name of the DynamoDB table"
  type        = string
}

variable "partition_key" {
  description = "Name of the partition key"
  type        = string
}

variable "partition_key_type" {
  description = "Type of the partition key"
  type        = string
}

variable "sort_key" {
  description = "Name of the sort key"
  type        = string
  default     = null
}

variable "sort_key_type" {
  description = "Type of the sort key"
  type        = string
  default     = null
}

variable "tags" {
  description = "A map of tags to assign to resources."
  type        = map(string)
  default     = {}
}
