resource "aws_acm_certificate" "imported_cert" {
  private_key       = aws_ssm_parameter.mtls_api_private_key_cert.value
  certificate_body  = aws_ssm_parameter.mtls_api_client_cert.value
  certificate_chain = aws_ssm_parameter.mtls_api_ca_cert.value

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Region        = local.region
    Stack         = local.stack_name
    CertificateType = "Imported"
  }
}

resource "aws_acm_certificate" "domain_validation" {
  domain_name       = "${var.environment}.eligibility-signposting-api.nhs.uk"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Region          = local.region
    Stack           = local.stack_name
    CertificateType = "DomainValidation"
  }
}
