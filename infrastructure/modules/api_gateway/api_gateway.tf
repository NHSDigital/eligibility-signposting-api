resource "aws_api_gateway_rest_api" "api_gateway" {
  name        = var.workspace == "default" ? "${var.api_gateway_name}-rest-api" : "${var.workspace}-${var.api_gateway_name}-rest-api"
  description = "The API Gateway for ${var.project_name} ${var.environment} environment"

  disable_execute_api_endpoint = var.disable_default_endpoint # We would want to disable this if we are using a custom domain name

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Stack = var.stack_name
  }
}

resource "aws_api_gateway_account" "api_gateway" {
  cloudwatch_role_arn = aws_iam_role.api_gateway.arn
}
