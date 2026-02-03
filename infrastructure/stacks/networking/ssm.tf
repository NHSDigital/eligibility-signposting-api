resource "aws_ssm_parameter" "proxygen_private_key" {
  for_each = var.environment == "dev" ? {
    ptl  = { path = "/ptl/proxygen/private_key", value = var.PROXYGEN_PRIVATE_KEY_PTL }
    prod = { path = "/prod/proxygen/private_key", value = var.PROXYGEN_PRIVATE_KEY_PROD }
  } : {}

  name   = each.value.path
  type   = "SecureString"
  key_id = aws_kms_key.networking_ssm_key.id
  value  = each.value.value

  tier  = "Advanced"

  tags = {
    Stack = local.stack_name
  }

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "mtls_api_ca_cert" {
  name   = "/${var.environment}/mtls/api_ca_cert"
  type   = "SecureString"
  key_id = aws_kms_key.networking_ssm_key.id
  value  = var.API_CA_CERT
  tier   = "Advanced"
  tags = {
  Stack = local.stack_name
  }

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "mtls_api_client_cert" {
  name   = "/${var.environment}/mtls/api_client_cert"
  type   = "SecureString"
  key_id = aws_kms_key.networking_ssm_key.id
  value  = var.API_CLIENT_CERT
  tier   = "Advanced"
  tags = {
    Stack = local.stack_name
  }

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "mtls_api_private_key_cert" {
  name   = "/${var.environment}/mtls/api_private_key_cert"
  type   = "SecureString"
  key_id = aws_kms_key.networking_ssm_key.id
  value  = var.API_PRIVATE_KEY_CERT
  tier   = "Advanced"
  tags = {
    Stack = local.stack_name
  }

  lifecycle {
    ignore_changes = [value]
  }
}
