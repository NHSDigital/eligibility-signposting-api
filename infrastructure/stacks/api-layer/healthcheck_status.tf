resource "aws_api_gateway_method" "_status" {
  rest_api_id   = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id   = aws_api_gateway_resource._status.id
  http_method   = "GET"
  authorization = "NONE"

  depends_on = [
    aws_api_gateway_resource._status,
  ]
}

resource "aws_api_gateway_integration" "_status" {
  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource._status.id
  http_method = aws_api_gateway_method._status.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "_status" {
  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource._status.id
  http_method = aws_api_gateway_method._status.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "_status" {
  rest_api_id = module.eligibility_signposting_api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource._status.id
  http_method = aws_api_gateway_method._status.http_method
  status_code = aws_api_gateway_method_response._status.status_code

  response_templates = {
    "application/json" = jsonencode({
      status    = "pass",
      version   = "",
      revision  = "",
      releaseId = "",
      commitId  = "",
      checks = {
        "healthcheckService:status" = [
          {
            status       = "pass",
            timeout      = false,
            responseCode = 200,
            outcome      = "<html><h1>Ok</h1></html>",
            links = {
              self = "http://healthcheckService.example.com/_status"
            }
          }
        ]
      }
    })
  }
}
