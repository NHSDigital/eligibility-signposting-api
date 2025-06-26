module "eligibility_signposting_api_gateway" {
  source                   = "../../modules/api_gateway"
  api_gateway_name         = "eligibility-signposting-api"
  disable_default_endpoint = var.environment == "dev" && local.workspace != "default" ? false : true
  workspace                = local.workspace
  stack_name               = local.stack_name
  environment              = var.environment
  tags                     = local.tags
}

resource "aws_api_gateway_resource" "_status" {
  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  parent_id   = module.eligibility_signposting_api_gateway.root_resource_id
  path_part   = "_status"
}

resource "aws_api_gateway_resource" "patient_check" {
  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  parent_id   = module.eligibility_signposting_api_gateway.root_resource_id
  path_part   = "patient-check"
}

resource "aws_api_gateway_resource" "patient" {
  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  parent_id   = aws_api_gateway_resource.patient_check.id
  path_part   = "{id}"
}

# deployment

resource "aws_api_gateway_deployment" "eligibility_signposting_api" {
  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_integration.get_patient_check.id,
      aws_api_gateway_integration._status.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "eligibility-signposting-api" {
  #checkov:skip=CKV2_AWS_51: mTLS is enforced at the custom domain, not at the stage level
  #checkov:skip=CKV_AWS_120: We're not enabling caching for this API Gateway, yet
  deployment_id        = aws_api_gateway_deployment.eligibility_signposting_api.id
  rest_api_id          = module.eligibility_signposting_api_gateway.rest_api_id
  stage_name           = "${local.workspace}-eligibility-signposting-api-live"
  xray_tracing_enabled = true

  access_log_settings {
    destination_arn = module.eligibility_signposting_api_gateway.cloudwatch_destination_arn
    format          = "{ \"requestId\":\"$context.requestId\", \"ip\": \"$context.identity.sourceIp\", \"caller\":\"$context.identity.caller\", \"user\":\"$context.identity.user\", \"requestTime\":\"$context.requestTime\", \"httpMethod\":\"$context.httpMethod\", \"resourcePath\":\"$context.resourcePath\", \"status\":\"$context.status\", \"protocol\":\"$context.protocol\", \"responseLength\":\"$context.responseLength\", \"accountId\":\"$context.accountId\", \"apiId\":\"$context.apiId\", \"stage\":\"$context.stage\", \"domainName\":\"$context.domainName\", \"error_message\":\"$context.error.message\", \"clientCertSerialNumber\":\"$context.identity.clientCert.serialNumber\", \"clientCertValidityNotBefore\":\"$context.identity.clientCert.validity.notBefore\", \"clientCertValidityNotAfter\":\"$context.identity.clientCert.validity.notAfter\" }"
  }

  depends_on = [
    module.eligibility_signposting_api_gateway.api_gateway_account,
    module.eligibility_signposting_api_gateway.logging_policy_attachment
  ]
}

resource "aws_api_gateway_method_settings" "check_eligibility" {
  #checkov:skip=CKV_AWS_225: We're not enabling caching for this API Gateway, yet
  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  stage_name  = aws_api_gateway_stage.eligibility-signposting-api.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled = true
    logging_level   = "INFO"
  }

  depends_on = [
    module.eligibility_signposting_api_gateway.api_gateway_account,
    module.eligibility_signposting_api_gateway.logging_policy_attachment
  ]
}

resource "aws_api_gateway_domain_name" "check_eligibility" {
  count                                  = var.environment == "dev" && local.workspace != "default" ? 0 : 1
  domain_name                            = "${local.api_subdomain}.${local.api_domain_name}"
  regional_certificate_arn               = data.aws_acm_certificate.imported_cert.arn
  ownership_verification_certificate_arn = data.aws_acm_certificate.validation_cert.arn

  mutual_tls_authentication {
    truststore_uri     = "s3://${module.s3_truststore_bucket.storage_bucket_name}/truststore.pem"
    truststore_version = aws_s3_object.pem_file.version_id
  }

  security_policy = "TLS_1_2"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_s3_object.pem_file,
    data.aws_acm_certificate.imported_cert,
    data.aws_acm_certificate.validation_cert,
    module.s3_truststore_bucket,
    module.eligibility_signposting_api_gateway
  ]
}

resource "aws_api_gateway_base_path_mapping" "eligibility-signposting-api" {
  count       = var.environment == "dev" && local.workspace != "default" ? 0 : 1
  api_id      = module.eligibility_signposting_api_gateway.rest_api_id
  stage_name  = aws_api_gateway_stage.eligibility-signposting-api.stage_name
  domain_name = "${local.api_subdomain}.${local.api_domain_name}"
}
