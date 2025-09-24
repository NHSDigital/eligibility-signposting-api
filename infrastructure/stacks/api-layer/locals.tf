locals {
  stack_name = "api-layer"

  api_subdomain   = var.environment
  api_domain_name = var.environment == "prod" ? "eligibility-signposting-api.national.nhs.uk" : "eligibility-signposting-api.nhs.uk"

  # PEM file for certificate
  pem_file_content = join("\n", [
    data.aws_ssm_parameter.mtls_api_client_cert.value,
    data.aws_ssm_parameter.mtls_api_ca_cert.value
  ])
}
