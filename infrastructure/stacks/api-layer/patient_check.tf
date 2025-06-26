
resource "aws_api_gateway_request_validator" "patient_check_validator" {
  rest_api_id                 = module.eligibility_signposting_api_gateway.rest_api_id
  name                        = "validate-path-params"
  validate_request_body       = false
  validate_request_parameters = true
}

resource "aws_api_gateway_method" "get_patient_check" {
  #checkov:skip=CKV_AWS_59: API is secured via Apigee proxy with mTLS, API keys are not used
  rest_api_id      = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id      = aws_api_gateway_resource.patient.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = false

  request_validator_id = aws_api_gateway_request_validator.patient_check_validator.id

  request_parameters = {
    "method.request.path.id" = true # Require the 'id' path parameter
  }

  depends_on = [
    aws_api_gateway_resource.patient,
    aws_api_gateway_resource.patient_check,
  ]
}

resource "aws_api_gateway_integration" "get_patient_check" {
  rest_api_id             = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id             = aws_api_gateway_resource.patient.id
  http_method             = aws_api_gateway_method.get_patient_check.http_method
  integration_http_method = "POST" # Needed for lambda proxy integration
  type                    = "AWS_PROXY"
  uri                     = module.eligibility_signposting_lambda_function.aws_lambda_invoke_arn

  depends_on = [
    aws_api_gateway_method.get_patient_check
  ]
}

resource "aws_lambda_permission" "get_patient_check" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.eligibility_signposting_lambda_function.aws_lambda_function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${module.eligibility_signposting_api_gateway.execution_arn}/*/*"
}
