# API Gateway Integration for Blue-Green Deployment
# This modifies the existing API Gateway to use Lambda aliases

# Update API Gateway integration to use production alias in production
resource "aws_api_gateway_integration" "get_patient_check_blue_green" {
  count = var.environment == "prod" ? 1 : 0

  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.patient.id
  http_method = aws_api_gateway_method.get_patient_check.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"

  # Use production alias for blue-green deployment
  uri = "arn:aws:apigateway:${data.aws_region.current.name}:lambda:path/2015-03-31/functions/${module.eligibility_signposting_lambda_function.lambda_function_arn}:production/invocations"
}

# Lambda permission for production alias
resource "aws_lambda_permission" "allow_api_gateway_production_alias" {
  count = var.environment == "prod" ? 1 : 0

  statement_id  = "AllowExecutionFromAPIGatewayProductionAlias"
  action        = "lambda:InvokeFunction"
  function_name = module.eligibility_signposting_lambda_function.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  qualifier     = aws_lambda_alias.production[0].name

  source_arn = "${module.eligibility_signposting_api_gateway.execution_arn}/*/*"
}

# Status endpoint integration for blue-green
resource "aws_api_gateway_integration" "_status_blue_green" {
  count = var.environment == "prod" ? 1 : 0

  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource._status.id
  http_method = aws_api_gateway_method._status.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"

  # Use production alias for blue-green deployment
  uri = "arn:aws:apigateway:${data.aws_region.current.name}:lambda:path/2015-03-31/functions/${module.eligibility_signposting_lambda_function.lambda_function_arn}:production/invocations"
}
