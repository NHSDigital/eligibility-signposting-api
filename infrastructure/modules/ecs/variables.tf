variable "eligibility_lambda_role_arn" {
  description = "lambda role arn"
  type        = string
}


variable "instance_name" {
  description = "Name of the instance"
  type        = string
}


variable "vpc_intra_subnets" {
  description = "vpc private subnets for lambda"
  type = list(string)
}

variable "security_group_ids" {
  description = "security groups for lambda"
  type = list(string)
}


variable "eligibility_rules_bucket_name" {
  description = "campaign config rules bucket name"
  type        = string
}

variable "eligibility_status_table_name" {
  description = "eligibility datastore table name"
  type        = string
}


variable "provisioned_concurrency_count" {
  description = "Number of prewarmed Lambda instances"
  type        = number
}

variable "ecr_repository_url" {
  description = "ecr repo url which contains the image"
  type        = string
}
