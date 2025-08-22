variable "splunk_hec_token" {
  type        = string
  description = "The HEC token for ITOC splunk"
  sensitive   = true
}
variable "splunk_hec_endpoint" {
  type        = string
  description = "The HEC endpoint url for ITOC splunk"
  sensitive   = true
}
