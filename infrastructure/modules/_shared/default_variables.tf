# tflint-ignore: terraform_unused_declarations
variable "project_name" {
  default = "eligibility-signposting-api"
  type    = string
}

# tflint-ignore: terraform_unused_declarations
variable "environment" {
  description = "The purpose of the account dev/test/ref/prod or the workspace"
  type        = string
}

# tflint-ignore: terraform_unused_declarations
variable "tags" {
  description = "A map of tags to assign to resources."
  type        = map(string)
  default     = {}
}
