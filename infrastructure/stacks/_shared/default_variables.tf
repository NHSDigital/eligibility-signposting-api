# tflint-ignore: terraform_unused_declarations
variable "project_name" {
  default = "eligibility-signposting-api"
  type    = string
}

variable "environment" {
  default     = "dev"
  description = "Environment"
  type        = string
}

variable "default_aws_region" {
  default     = "eu-west-2"
  description = "Default AWS region"
  type        = string
}
