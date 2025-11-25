variable "external_write_access_role_arn" {
  description = "Arn of the external write access role to provide secret manager access"
  type        = string
}

variable "eligibility_lambda_role_arn" {
  description = "Arn of the lambda role to provide secret manager access"
  type        = string
}
