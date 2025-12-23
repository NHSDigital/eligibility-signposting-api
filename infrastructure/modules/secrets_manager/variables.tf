variable "external_write_access_role_arn" {
  description = "List of ARNs for external write access roles"
  type = list(string)
}

variable "eligibility_lambda_role_arn" {
  description = "Arn of the lambda role to provide secret manager access"
  type        = string
}
