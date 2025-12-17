# Gateway Responses with Security Headers
# These responses are used when API Gateway itself returns an error (e.g., validation failures, auth errors)
# They ensure security headers are present even on API Gateway-generated error responses

resource "aws_api_gateway_gateway_response" "response_4xx" {
  rest_api_id   = module.eligibility_signposting_api_gateway.rest_api_id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Cache-Control"             = "'no-store, private'"
    "gatewayresponse.header.Strict-Transport-Security" = "'max-age=31536000; includeSubDomains'"
    "gatewayresponse.header.X-Content-Type-Options"    = "'nosniff'"
  }

  lifecycle {
    ignore_changes = [response_templates]
  }
}

resource "aws_api_gateway_gateway_response" "response_5xx" {
  rest_api_id   = module.eligibility_signposting_api_gateway.rest_api_id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Cache-Control"             = "'no-store, private'"
    "gatewayresponse.header.Strict-Transport-Security" = "'max-age=31536000; includeSubDomains'"
    "gatewayresponse.header.X-Content-Type-Options"    = "'nosniff'"
  }

  lifecycle {
    ignore_changes = [response_templates]
  }
}

resource "aws_api_gateway_gateway_response" "unauthorized" {
  rest_api_id   = module.eligibility_signposting_api_gateway.rest_api_id
  response_type = "UNAUTHORIZED"
  status_code   = "401"

  response_parameters = {
    "gatewayresponse.header.Cache-Control"             = "'no-store, private'"
    "gatewayresponse.header.Strict-Transport-Security" = "'max-age=31536000; includeSubDomains'"
    "gatewayresponse.header.X-Content-Type-Options"    = "'nosniff'"
  }

  lifecycle {
    ignore_changes = [response_templates]
  }
}

resource "aws_api_gateway_gateway_response" "access_denied" {
  rest_api_id   = module.eligibility_signposting_api_gateway.rest_api_id
  response_type = "ACCESS_DENIED"
  status_code   = "403"

  response_parameters = {
    "gatewayresponse.header.Cache-Control"             = "'no-store, private'"
    "gatewayresponse.header.Strict-Transport-Security" = "'max-age=31536000; includeSubDomains'"
    "gatewayresponse.header.X-Content-Type-Options"    = "'nosniff'"
  }

  lifecycle {
    ignore_changes = [response_templates]
  }
}

resource "aws_api_gateway_gateway_response" "throttled" {
  rest_api_id   = module.eligibility_signposting_api_gateway.rest_api_id
  response_type = "THROTTLED"
  status_code   = "429"

  response_parameters = {
    "gatewayresponse.header.Cache-Control"             = "'no-store, private'"
    "gatewayresponse.header.Strict-Transport-Security" = "'max-age=31536000; includeSubDomains'"
    "gatewayresponse.header.X-Content-Type-Options"    = "'nosniff'"
  }

  lifecycle {
    ignore_changes = [response_templates]
  }
}
