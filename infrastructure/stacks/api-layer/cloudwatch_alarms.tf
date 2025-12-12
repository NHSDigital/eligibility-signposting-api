locals {
  # Security alarms based on CloudTrail custom metrics
  cloudwatch_alarm_config = {
    UnauthorizedApiCalls = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "Unauthorized API calls detected - immediate alert on any occurrence"
      actions_enabled     = false # Disabling as cloudhealth role is triggering this alarm
    }
    ConsoleAuthenticationFailures = {
      threshold           = 3
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "Multiple console authentication failures detected within 5 minutes"
      actions_enabled     = true
    }
    CloudTrailConfigChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "CloudTrail configuration changes detected - immediate alert"
      actions_enabled     = true
    }
    VPCChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "VPC configuration changes detected"
      actions_enabled     = true
    }
    AWSConfigChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "AWS Config service changes detected"
      actions_enabled     = true
    }
    ModificationOfCMKs = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "KMS Customer Managed Key modifications detected - critical security alert"
      actions_enabled     = true
    }
    UnsuccessfulSwitchRole = {
      threshold           = 5
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 900
      statistic           = "Sum"
      alarm_description   = "Multiple unsuccessful role switch attempts detected within 15 minutes"
      actions_enabled     = true
    }
    ConsoleLoginNoMFA = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "Console login without MFA detected - security policy violation"
      actions_enabled     = true
    }
    RootAccountUsage = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "Root account usage detected - immediate critical alert"
      actions_enabled     = true
    }
    SecurityGroupChange = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "Security group changes detected"
      actions_enabled     = true
    }
    RouteTableChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "Route table changes detected"
      actions_enabled     = true
    }
    IAMPolicyChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "IAM policy changes detected - immediate security alert"
      actions_enabled     = true
    }
    s3BucketPolicyChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "S3 bucket policy changes detected"
      actions_enabled     = true
    }
    ChangesToNetworkGateways = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "Network gateway changes detected"
      actions_enabled     = true
    }
    ChangesToNACLs = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "Network ACL changes detected"
      actions_enabled     = true
    }
    KMSKeyPolicyChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "KMS key policy changes detected - critical security alert"
      actions_enabled     = true
    }
    s3PublicAccessChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "S3 public access changes detected - potential data exposure risk"
      actions_enabled     = true
    }
    CloudWatchAlarmChanges = {
      threshold           = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 300
      statistic           = "Sum"
      alarm_description   = "CloudWatch alarm configuration changes detected"
      actions_enabled     = true
    }
    LambdaFunctionChanges = {
      threshold           = 2
      comparison_operator = "GreaterThanOrEqualToThreshold"
      evaluation_periods  = 1
      period              = 600
      statistic           = "Sum"
      alarm_description   = "Multiple Lambda function changes detected within 10 minutes"
      actions_enabled     = true
    }
  }

  # API Gateway alarm configuration
  api_gateway_alarm_config = {
    "5XXError" = {
      metric_name         = "5XXError"
      namespace           = "AWS/ApiGateway"
      statistic           = "Sum"
      threshold           = 0
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 1
      period              = 300
      alarm_description   = "API Gateway 5XX errors detected - critical server-side issues"
      severity            = "critical"
      treat_missing_data  = "notBreaching"
    }
    "4XXError" = {
      metric_name         = "4XXError"
      namespace           = "AWS/ApiGateway"
      statistic           = "Sum"
      threshold           = 50 # Adjust based on expected traffic
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 2
      period              = 300
      alarm_description   = "High rate of API Gateway 4XX errors - client-side issues or auth problems"
      severity            = "high"
      treat_missing_data  = "notBreaching"
    }
    "LatencyP95" = {
      metric_name         = "Latency"
      namespace           = "AWS/ApiGateway"
      statistic           = "Average" # Use Average for ExtendedStatistic
      extended_statistic  = "p95"
      threshold           = 1000
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 1
      period              = 300
      alarm_description   = "API Gateway P95 latency > 1000ms - performance degradation"
      severity            = "high"
      treat_missing_data  = "notBreaching"
    }
    "IntegrationLatencyP95" = {
      metric_name         = "IntegrationLatency"
      namespace           = "AWS/ApiGateway"
      statistic           = "Average" # Use Average for ExtendedStatistic
      extended_statistic  = "p95"
      threshold           = 900
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 1
      period              = 300
      alarm_description   = "API Gateway backend (Lambda) P95 latency > 900ms - backend performance issues"
      severity            = "high"
      treat_missing_data  = "notBreaching"
    }
    "CountDrop" = {
      metric_name         = "Count"
      namespace           = "AWS/ApiGateway"
      statistic           = "Sum"
      threshold           = 10 # Minimum expected requests per 5min - adjust when live
      comparison_operator = "LessThanThreshold"
      evaluation_periods  = 2
      period              = 300
      alarm_description   = "API Gateway request volume drop - possible outage (enable when service is live)"
      severity            = "high"
      treat_missing_data  = "breaching" # Missing data could indicate outage
      actions_enabled     = false       # Disable until service is live
    }
  }

  # Lambda alarm configuration
  lambda_alarm_config = {
    "Errors" = {
      metric_name         = "Errors"
      namespace           = "AWS/Lambda"
      statistic           = "Sum"
      threshold           = 0
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 1
      period              = 300
      alarm_description   = "Lambda invocation errors detected - critical function failures"
      severity            = "critical"
      treat_missing_data  = "notBreaching"
    }
    "Throttles" = {
      metric_name         = "Throttles"
      namespace           = "AWS/Lambda"
      statistic           = "Sum"
      threshold           = 0
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 1
      period              = 300
      alarm_description   = "Lambda throttling detected - concurrency limits reached"
      severity            = "critical"
      treat_missing_data  = "notBreaching"
    }
    "Duration" = {
      metric_name         = "Duration"
      namespace           = "AWS/Lambda"
      statistic           = "Average"
      threshold           = 27000 # 90% of 30s timeout (adjust based on actual timeout)
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 2
      period              = 300
      alarm_description   = "Lambda duration approaching timeout - function performance warning"
      severity            = "warning"
      treat_missing_data  = "notBreaching"
    }
    "InvocationsDrop" = {
      metric_name         = "Invocations"
      namespace           = "AWS/Lambda"
      statistic           = "Sum"
      threshold           = 5 # Minimum expected invocations per 5min - adjust when live
      comparison_operator = "LessThanThreshold"
      evaluation_periods  = 2
      period              = 300
      alarm_description   = "Lambda invocation volume drop - possible outage (enable when service is live)"
      severity            = "high"
      treat_missing_data  = "breaching" # Missing data could indicate outage
      actions_enabled     = false       # Disable until service is live
    }
  }

  # ACM alarm configuration
  acm_alarm_config = {
    "CertificateExpiry44Days" = {
      metric_name         = "DaysToExpiry"
      namespace           = "AWS/CertificateManager"
      statistic           = "Minimum"
      threshold           = 44
      comparison_operator = "LessThanThreshold"
      evaluation_periods  = 1
      period              = 86400 # one day in seconds
      alarm_description   = "ACM Certificate expiring within 44 days"
      severity            = "warning"
      treat_missing_data  = "notBreaching"
    }

    "CertificateExpiry30Days" = {
      metric_name         = "DaysToExpiry"
      namespace           = "AWS/CertificateManager"
      statistic           = "Minimum"
      threshold           = 30
      comparison_operator = "LessThanThreshold"
      evaluation_periods  = 1
      period              = 86400 # one day in seconds
      alarm_description   = "ACM Certificate expiring within 30 days"
      severity            = "high"
      treat_missing_data  = "notBreaching"
    }

    "CertificateExpiry7Days" = {
      metric_name         = "DaysToExpiry"
      namespace           = "AWS/CertificateManager"
      statistic           = "Minimum"
      threshold           = 7
      comparison_operator = "LessThanThreshold"
      evaluation_periods  = 1
      period              = 86400 # one day in seconds
      alarm_description   = "ACM Certificate expiring within 7 days"
      severity            = "critical"
      treat_missing_data  = "notBreaching"
    }
  }
}


# SNS Topic for CloudWatch Alarms
resource "aws_sns_topic" "cloudwatch_alarms" {
  name = "cloudwatch-security-alarms"

  kms_master_key_id = aws_kms_key.sns_encryption_key.id

  tags = {
    Environment = var.environment
    Purpose     = "security-alerting"
    ManagedBy   = "terraform"
  }
}

resource "aws_kms_key" "sns_encryption_key" {
  description             = "KMS key for encrypting CloudWatch alarms SNS topic"
  deletion_window_in_days = 7
  enable_key_rotation     = true


  tags = {
    Name        = "cloudwatch-alarms-sns-encryption-key"
    Environment = var.environment
    Purpose     = "sns-encryption"
    ManagedBy   = "terraform"
  }
}

# Security Alarms (CloudTrail-based)
resource "aws_cloudwatch_metric_alarm" "cloudtrail_custom_metric_alarms" {
  # checkov:skip=CKV_AWS_319: Disabling some alarms until service is live
  for_each = local.cloudwatch_alarm_config

  alarm_name          = "SecurityAlert-${each.key}"
  alarm_description   = each.value.alarm_description
  actions_enabled     = each.value.actions_enabled
  metric_name         = each.key
  namespace           = "security"
  statistic           = each.value.statistic
  period              = each.value.period
  evaluation_periods  = each.value.evaluation_periods
  threshold           = each.value.threshold
  comparison_operator = each.value.comparison_operator

  # Treat missing data as not breaching (common for security metrics)
  treat_missing_data = "notBreaching"

  # Add standard tags for organization
  tags = {
    Environment = "production"
    AlertType   = "security"
    Severity    = contains(["RootAccountUsage", "ModificationOfCMKs", "KMSKeyPolicyChanges", "ConsoleLoginNoMFA"], each.key) ? "critical" : "high"
    ManagedBy   = "terraform"
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]
}

# API Gateway CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "api_gateway_alarms" {
  # checkov:skip=CKV_AWS_319: Disabling some alarms until service is live
  for_each = local.api_gateway_alarm_config

  alarm_name          = "APIGateway-${each.key}"
  alarm_description   = each.value.alarm_description
  actions_enabled     = lookup(each.value, "actions_enabled", true)
  metric_name         = each.value.metric_name
  namespace           = each.value.namespace
  statistic           = lookup(each.value, "extended_statistic", null) == null ? each.value.statistic : null
  extended_statistic  = lookup(each.value, "extended_statistic", null)
  period              = each.value.period
  evaluation_periods  = each.value.evaluation_periods
  threshold           = each.value.threshold
  comparison_operator = each.value.comparison_operator
  treat_missing_data  = each.value.treat_missing_data

  # Add dimensions for API Gateway
  dimensions = {
    ApiName = "eligibility-signposting-api"
  }

  tags = {
    Environment = var.environment
    AlertType   = "performance"
    Service     = "api-gateway"
    Severity    = each.value.severity
    ManagedBy   = "terraform"
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]
}

# Lambda CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_alarms" {
  # checkov:skip=CKV_AWS_319: Disabling some alarms until service is live
  for_each = local.lambda_alarm_config

  alarm_name          = "Lambda-${each.key}"
  alarm_description   = each.value.alarm_description
  actions_enabled     = lookup(each.value, "actions_enabled", true)
  metric_name         = each.value.metric_name
  namespace           = each.value.namespace
  statistic           = each.value.statistic
  period              = each.value.period
  evaluation_periods  = each.value.evaluation_periods
  threshold           = each.value.threshold
  comparison_operator = each.value.comparison_operator
  treat_missing_data  = each.value.treat_missing_data

  # Add dimensions for Lambda
  dimensions = {
    FunctionName = module.eligibility_signposting_lambda_function.aws_lambda_function_name
  }

  tags = {
    Environment = var.environment
    AlertType   = "performance"
    Service     = "lambda"
    Severity    = each.value.severity
    ManagedBy   = "terraform"
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]
}

# ACM CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "acm_expiry_alarms" {
  for_each = local.acm_alarm_config

  alarm_name          = "ACM-${each.key}"
  alarm_description   = each.value.alarm_description
  namespace           = each.value.namespace
  metric_name         = each.value.metric_name
  statistic           = each.value.statistic
  threshold           = each.value.threshold
  comparison_operator = each.value.comparison_operator
  evaluation_periods  = each.value.evaluation_periods
  period              = each.value.period
  treat_missing_data  = each.value.treat_missing_data

  dimensions = {
    CertificateArn = data.aws_acm_certificate.imported_cert.arn
  }

  tags = {
    Environment = var.environment
    AlertType   = "security"
    Service     = "acm"
    Severity    = each.value.severity
    ManagedBy   = "terraform"
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]
}

# Splunk backup S3 bucket delivery failure alarm
resource "aws_cloudwatch_metric_alarm" "splunk_backup_delivery_failure" {
  alarm_name          = "SplunkBackupS3DeliveryFailure"
  alarm_description   = "Triggers when there is a delivery failure from Firehose to the Splunk backup S3 bucket"
  namespace           = "AWS/Firehose"
  metric_name         = "DeliveryToS3.Failed"
  statistic           = "Sum"
  period              = 300 # 5 minutes
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DeliveryStreamName = module.splunk_forwarder.firehose_delivery_stream_name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = {
    Environment = var.environment
    AlertType   = "data-delivery"
    Service     = "firehose"
    Severity    = "high"
    ManagedBy   = "terraform"
  }
}
