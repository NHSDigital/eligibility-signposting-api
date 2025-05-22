variable "project_name" {
  default = "eligibility-signposting-api"
  type    = string
}

variable "environment" {
  description = "The purpose of the account dev/test/ref/prod or the workspace"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to resources."
  type        = map(string)
  default     = {}
}

variable "workspace" {
  description = "Usually the developer short code or the name of the environment."
  type        = string
}

variable "stack_name" {
  description = "The name of the stack being deployed"
  type        = string
}

variable "region" {
  type        = string
  description = "The aws region."
  default     = "eu-west-2"
}
