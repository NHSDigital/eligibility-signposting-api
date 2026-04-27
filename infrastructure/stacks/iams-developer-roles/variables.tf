# Variables for IAMs developer roles
variable "github_org" {
  default     = "NHSDigital"
  description = "GitHub organization"
  type        = string
}
variable "github_repo" {
  default     = "eligibility-signposting-api"
  description = "GitHub repository"
  type        = string
}

variable "regression_repo" {
  default     = "eligibility-signposting-api-regression-tests"
  description = "GitHub repository"
  type        = string
}
