# CloudWatch Alarms for WAF Metrics
# These alarms help monitor WAF activity and potential security threats

# Alarm for blocked requests by IP Reputation List
resource "aws_cloudwatch_metric_alarm" "waf_ip_reputation_blocks" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-IPReputationList-Blocks-${local.workspace}"
  alarm_description   = "Alerts when malicious IPs are blocked by AWS IP Reputation List"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 10 # Alert after 10 blocked requests
  treat_missing_data  = "notBreaching"

  dimensions = {
    Region = var.default_aws_region
    Rule   = "AWSManagedRulesAmazonIpReputationList"
    WebACL = aws_wafv2_web_acl.api_gateway[0].name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = merge(
    local.tags,
    {
      Name        = "WAF-IPReputationList-Blocks"
      Severity    = "high"
      Environment = var.environment
    }
  )
}

# Alarm for blocked requests by Core Rule Set (OWASP)
resource "aws_cloudwatch_metric_alarm" "waf_core_ruleset_blocks" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-CoreRuleSet-Blocks-${local.workspace}"
  alarm_description   = "Alerts when requests are blocked by Core Rule Set (OWASP Top 10)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 20 # Alert after 20 blocked requests
  treat_missing_data  = "notBreaching"

  dimensions = {
    Region = var.default_aws_region
    Rule   = "AWSManagedRulesCommonRuleSet"
    WebACL = aws_wafv2_web_acl.api_gateway[0].name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = merge(
    local.tags,
    {
      Name        = "WAF-CoreRuleSet-Blocks"
      Severity    = "high"
      Environment = var.environment
    }
  )
}

# Alarm for blocked requests by Known Bad Inputs
resource "aws_cloudwatch_metric_alarm" "waf_bad_inputs_blocks" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-KnownBadInputs-Blocks-${local.workspace}"
  alarm_description   = "Alerts when requests are blocked by Known Bad Inputs rule"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    Region = var.default_aws_region
    Rule   = "AWSManagedRulesKnownBadInputsRuleSet"
    WebACL = aws_wafv2_web_acl.api_gateway[0].name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = merge(
    local.tags,
    {
      Name        = "WAF-KnownBadInputs-Blocks"
      Severity    = "high"
      Environment = var.environment
    }
  )
}

# Alarm for rate limit violations (overall)
resource "aws_cloudwatch_metric_alarm" "waf_rate_limit_blocks" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-RateLimit-Blocks-${local.workspace}"
  alarm_description   = "Alerts when requests are rate-limited (potential DDoS)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 50 # Alert after 50 rate-limited requests
  treat_missing_data  = "notBreaching"

  dimensions = {
    Region = var.default_aws_region
    Rule   = "RateLimitRule"
    WebACL = aws_wafv2_web_acl.api_gateway[0].name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = merge(
    local.tags,
    {
      Name        = "WAF-RateLimit-Blocks"
      Severity    = "critical"
      Environment = var.environment
    }
  )
}

# Alarm for non-UK rate limit violations
resource "aws_cloudwatch_metric_alarm" "waf_non_uk_counted" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-NonUK-CountedRequests-${local.workspace}"
  alarm_description   = "Alerts when non-UK requests are observed (COUNT mode) by geo rule"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CountedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 30
  treat_missing_data  = "notBreaching"

  dimensions = {
    Region = var.default_aws_region
    Rule   = "MonitorNonUK"
    WebACL = aws_wafv2_web_acl.api_gateway[0].name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = merge(
    local.tags,
    {
      Name        = "WAF-NonUK-CountedRequests"
      Severity    = "medium"
      Environment = var.environment
    }
  )
}

# Alarm for high volume of all requests (monitoring)
resource "aws_cloudwatch_metric_alarm" "waf_all_requests_high" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-AllRequests-High-${local.workspace}"
  alarm_description   = "Monitors total request volume through WAF"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "AllowedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 10000 # Adjust based on expected traffic
  treat_missing_data  = "notBreaching"

  dimensions = {
    Region = var.default_aws_region
    WebACL = aws_wafv2_web_acl.api_gateway[0].name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = merge(
    local.tags,
    {
      Name        = "WAF-AllRequests-High"
      Severity    = "medium"
      Environment = var.environment
    }
  )
}

# Alarm for monitoring counted requests (during initial count mode)
# This helps identify if rules would block legitimate traffic
resource "aws_cloudwatch_metric_alarm" "waf_counted_requests_monitoring" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-CountedRequests-Monitoring-${local.workspace}"
  alarm_description   = "Monitors requests that would be blocked if rules were active (COUNT mode)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CountedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 100 # Alert if many requests would be blocked
  treat_missing_data  = "notBreaching"

  dimensions = {
    Region = var.default_aws_region
    WebACL = aws_wafv2_web_acl.api_gateway[0].name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = merge(
    local.tags,
    {
      Name        = "WAF-CountedRequests-Monitoring"
      Severity    = "low"
      Environment = var.environment
      Purpose     = "Initial monitoring during COUNT mode phase"
    }
  )
}
