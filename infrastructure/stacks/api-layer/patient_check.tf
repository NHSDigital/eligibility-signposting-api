resource "aws_api_gateway_method" "get_patient_check" {
  rest_api_id      = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id      = aws_api_gateway_resource.patient.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = false

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
  uri                     = module.get_patient_check.invoke_arn # placeholder for the actual lambda function ARN

  depends_on = [
    aws_api_gateway_method.get_patient_check
  ]
}

resource "aws_lambda_permission" "get_patient_check" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.get_patient_check.function_name # placeholder for the actual lambda function name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${module.eligibility_signposting_api_gateway.execution_arn}/*/*"
}
