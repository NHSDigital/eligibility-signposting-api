data "aws_caller_identity" "current" {}

data "aws_acm_certificate" "imported_cert" {
  domain    = "${var.environment}.${local.api_domain_name}"
  types     = ["IMPORTED"]
  provider  = aws.eu-west-2
  key_types = ["RSA_4096"]
}

data "aws_acm_certificate" "validation_cert" {
  domain      = "${var.environment}.${local.api_domain_name}"
  types       = ["AMAZON_ISSUED"]
  provider    = aws.eu-west-2
  key_types   = ["RSA_2048"]
  most_recent = true
}

data "aws_ssm_parameter" "mtls_api_client_cert" {
  name            = "/${var.environment}/mtls/api_client_cert"
  with_decryption = true
}

data "aws_ssm_parameter" "mtls_api_ca_cert" {
  name            = "/${var.environment}/mtls/api_ca_cert"
  with_decryption = true
}

data "aws_lambda_function" "eligibility_signposting_lambda" {
  function_name = terraform.workspace == "default" ? "eligibility_signposting_api" : "${terraform.workspace}-eligibility_signposting_api"
}
