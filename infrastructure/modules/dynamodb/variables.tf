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
