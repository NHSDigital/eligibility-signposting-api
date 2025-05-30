variable "API_CA_CERT" {
  type        = string
  description = "The Certificate Authority (CA) Root for the Client Certificate with Intermediate Certificate"
  sensitive   = true
}
variable "API_CLIENT_CERT" {
  type        = string
  description = "The signed Client Certificate"
  sensitive   = true
}
variable "API_PRIVATE_KEY_CERT" {
  type        = string
  description = "The private key for the signed Client Certificate"
  sensitive   = true
}
