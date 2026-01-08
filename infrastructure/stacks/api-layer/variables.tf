variable "SPLUNK_HEC_TOKEN" {
  type        = string
  description = "The HEC token for ITOC splunk"
  sensitive   = true
}
variable "SPLUNK_HEC_ENDPOINT" {
  type        = string
  description = "The HEC endpoint url for ITOC splunk"
  sensitive   = true
}

# WAF deployment environments (list of environment names where WAF should be deployed)
variable "waf_enabled_environments" {
  type        = list(string)
  description = "Environments in which WAF resources are deployed. Adjust to disable in test after evaluation."
  default     = ["dev", "preprod", "prod"]
}

variable "operator_emails" {
  description = "List of email addresses to receive manual approval notifications"
  type        = list(string)
  default = ["tom.eldridge1@nhs.net", "shweta.dongare1@nhs.net"]
}
