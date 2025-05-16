locals {
  stack_name = "api-layer"

  api_subdomain   = var.environment == local.workspace ? local.workspace : "${local.workspace}.${var.environment}"
  api_domain_name = "eligibility-signposting-api.nhs.uk"

  # PEM file for certificate
  pem_file_content = join("\n", [
    data.aws_ssm_parameter.mtls_api_client_cert.value,
    data.aws_ssm_parameter.mtls_api_ca_cert.value
  ])
}
