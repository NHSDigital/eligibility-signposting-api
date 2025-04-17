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
