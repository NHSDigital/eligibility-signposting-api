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
