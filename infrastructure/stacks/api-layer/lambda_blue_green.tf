# Blue-Green Deployment Configuration for Production
# This file implements Lambda aliases and weighted routing for zero-downtime deployments

locals {
  # Only enable blue-green for production
  enable_blue_green = var.environment == "prod"

  # Traffic distribution - adjust during deployment
  blue_weight  = var.blue_traffic_weight
  green_weight = 100 - var.blue_traffic_weight
}

# Lambda Alias for Blue (stable) version
resource "aws_lambda_alias" "blue" {
  count = local.enable_blue_green ? 1 : 0

  name             = "blue"
  description      = "Blue environment - stable production version"
  function_name    = module.eligibility_signposting_lambda_function.lambda_function_name
  function_version = var.blue_lambda_version
}

# Lambda Alias for Green (new) version
resource "aws_lambda_alias" "green" {
  count = local.enable_blue_green ? 1 : 0

  name             = "green"
  description      = "Green environment - new deployment version"
  function_name    = module.eligibility_signposting_lambda_function.lambda_function_name
  function_version = var.green_lambda_version
}

# Production Alias with weighted routing between Blue and Green
resource "aws_lambda_alias" "production" {
  count = local.enable_blue_green ? 1 : 0

  name             = "production"
  description      = "Production alias with blue-green traffic routing"
  function_name    = module.eligibility_signposting_lambda_function.lambda_function_name
  function_version = var.blue_lambda_version

  # Weighted routing configuration
  routing_config {
    additional_version_weights = {
      "${var.green_lambda_version}" = local.green_weight
    }
  }
}

# CloudWatch Alarms for Blue-Green Monitoring
resource "aws_cloudwatch_metric_alarm" "blue_error_rate" {
  count = local.enable_blue_green ? 1 : 0

  alarm_name          = "lambda-blue-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda blue environment error rate"

  dimensions = {
    FunctionName = module.eligibility_signposting_lambda_function.lambda_function_name
    Resource     = "${module.eligibility_signposting_lambda_function.lambda_function_name}:blue"
  }

  alarm_actions = [aws_sns_topic.blue_green_alerts[0].arn]

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "green_error_rate" {
  count = local.enable_blue_green ? 1 : 0

  alarm_name          = "lambda-green-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda green environment error rate"

  dimensions = {
    FunctionName = module.eligibility_signposting_lambda_function.lambda_function_name
    Resource     = "${module.eligibility_signposting_lambda_function.lambda_function_name}:green"
  }

  alarm_actions = [aws_sns_topic.blue_green_alerts[0].arn]

  tags = local.tags
}

# SNS Topic for Blue-Green Alerts
resource "aws_sns_topic" "blue_green_alerts" {
  count = local.enable_blue_green ? 1 : 0

  name = "blue-green-deployment-alerts-${var.environment}"

  tags = local.tags
}
