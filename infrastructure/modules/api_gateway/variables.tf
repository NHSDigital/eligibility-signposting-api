variable "api_gateway_name" {
  type        = string
  description = "The name of the API Gateway"
}

variable "disable_default_endpoint" {
  type        = bool
  description = "Indicates whether the default endpoint the API Gateway generates should be disabled. If true, the API will need to be called from a Custom Domain Name"
}

variable "trust_store_pem_arn" {
  type        = string
  description = "the trust store pem arn, for providing decrypt permission ot api gateway"

}
