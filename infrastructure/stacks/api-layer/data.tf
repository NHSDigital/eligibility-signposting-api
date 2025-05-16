data "aws_caller_identity" "current" {}

data "aws_acm_certificate" "imported_cert" {
  domain      = "${var.environment}.${local.api_domain_name}"
  types       = ["IMPORTED"]
  provider    = aws.eu-west-2
}

data "aws_acm_certificate" "validation_cert" {
  domain      = "${var.environment}.${local.api_domain_name}"
  types       = ["AMAZON_ISSUED"]
  provider    = aws.eu-west-2
  key_types   = ["RSA_2048"]
  most_recent = true
}

data "aws_ssm_parameter" "mtls_api_client_cert" {
  name = "/${var.environment}/mtls/api_client_cert"
}

data "aws_ssm_parameter" "mtls_api_ca_cert" {
  name = "/${var.environment}/mtls/api_ca_cert"
}
