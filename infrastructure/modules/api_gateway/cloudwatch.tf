resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.workspace}-${var.api_gateway_name}"
  retention_in_days = 365
  tags              = var.tags
  kms_key_id        = aws_kms_key.api_gateway.arn

  lifecycle {
    prevent_destroy = false
  }
}
