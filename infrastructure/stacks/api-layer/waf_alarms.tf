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
# Rate limit is set to 300,000 req/5min (1000 TPS headroom over 500 TPS peak).
# Any block at this threshold is a serious incident - a single IP would need to exceed
# 300k requests in 5 minutes, which indicates a runaway or compromised proxy.
resource "aws_cloudwatch_metric_alarm" "waf_rate_limit_blocks" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-RateLimit-Blocks-${local.workspace}"
  alarm_description   = "Alerts when requests are rate-limited - at 300k/5min limit this indicates a runaway or compromised proxy"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 1 # Any block at this limit is a serious incident
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

# Alarm for blocked non-UK requests
# In preprod US is also allowed (for GitHub Actions), so this alarm fires on traffic
# from countries outside GB+US. In prod it fires on anything outside GB.
resource "aws_cloudwatch_metric_alarm" "waf_non_uk_blocked" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-NonUK-BlockedRequests-${local.workspace}"
  alarm_description   = "Alerts when non-UK requests are blocked by geo rule - may indicate stolen mTLS cert use from outside UK"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 30
  treat_missing_data  = "notBreaching"

  dimensions = {
    Region = var.default_aws_region
    Rule   = "BlockNonUK"
    WebACL = aws_wafv2_web_acl.api_gateway[0].name
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = merge(
    local.tags,
    {
      Name        = "WAF-NonUK-BlockedRequests"
      Severity    = "high"
      Environment = var.environment
    }
  )
}

# Alarm for high volume of all requests (monitoring)
resource "aws_cloudwatch_metric_alarm" "waf_all_requests_high" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-AllRequests-High-${local.workspace}"
  alarm_description   = "Monitors total allowed request volume through WAF"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "AllowedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 300000 # 2x peak (500 TPS = 150k/5min); alert above 300k/5min
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

# Alarm for counted requests (NoUserAgent_Header override)
# The CRS NoUserAgent_Header sub-rule is kept in COUNT to allow the API proxy healthcheck.
# This alarm alerts if count spikes unexpectedly, which could indicate rule misconfiguration
# or unexpected traffic patterns hitting that override.
resource "aws_cloudwatch_metric_alarm" "waf_counted_requests_monitoring" {
  count               = local.waf_enabled ? 1 : 0
  alarm_name          = "WAF-CountedRequests-Monitoring-${local.workspace}"
  alarm_description   = "Monitors counted requests - expected to be low volume (healthcheck NoUserAgent_Header override only)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CountedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 100 # Alert if count spikes beyond normal healthcheck frequency
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
      Purpose     = "Monitor NoUserAgent_Header count override for healthcheck proxy"
    }
  )
}
