# WAF Web ACL for API Gateway
# Only deployed in production environment for cost optimization
# Initially all rules are in COUNT mode to monitor traffic patterns

resource "aws_wafv2_web_acl" "api_gateway" {
  count       = local.waf_enabled ? 1 : 0
  name        = "${local.workspace}-eligibility-signposting-api-waf"
  description = "WAF Web ACL for Eligibility Signposting API Gateway - Production"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # Rule 1: AWS Managed - Amazon IP Reputation List
  # Blocks requests from IP addresses known to be malicious
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 10

    override_action {
      count {} # Start in count mode - change to none {} when ready to block
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesAmazonIpReputationList"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesAmazonIpReputationList"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: AWS Managed - Core Rule Set (includes OWASP Top 10)
  # Protects against common web exploits
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 20

    override_action {
      count {} # Start in count mode - change to none {} when ready to block
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: AWS Managed - Known Bad Inputs
  # Blocks request patterns known to be invalid or associated with exploitation
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 30

    # Enforce BLOCK for Known Bad Inputs to mitigate Log4j (CKV_AWS_192)
    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: Rate-Based Rule - Overall rate limiting
  # Protects against DDoS and brute force attacks
  # Default: 2000 requests per 5 minutes per IP (adjust based on your traffic)
  rule {
    name     = "RateLimitRule"
    priority = 40

    action {
      count {} # Start in count mode - change to block {} when ready
    }

    statement {
      rate_based_statement {
        limit              = 2000 # Requests per 5-minute period per IP
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  # Rule 5: Geographic Monitoring Rule - Monitor non-UK traffic (COUNT only)
  # NHS-specific requirement: initially monitor requests originating from outside GB
  # This rule COUNTS any request whose geo country code is not GB (does not block)
  rule {
    name     = "MonitorNonUK"
    priority = 50

    action {
      count {}
    }

    statement {
      not_statement {
        statement {
          geo_match_statement {
            country_codes = ["GB"] # United Kingdom only (does NOT include Crown Dependencies)
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "MonitorNonUK"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.workspace}-eligibility-signposting-api-waf"
    sampled_requests_enabled   = true
  }

  tags = merge(
    local.tags,
    {
      Name        = "${local.workspace}-eligibility-signposting-api-waf"
      Stack       = local.stack_name
      Environment = var.environment
      Purpose     = "API Gateway WAF protection"
    }
  )
}

# Associate WAF with API Gateway Stage
resource "aws_wafv2_web_acl_association" "api_gateway" {
  count        = local.waf_enabled ? 1 : 0
  resource_arn = aws_api_gateway_stage.eligibility-signposting-api.arn
  web_acl_arn  = aws_wafv2_web_acl.api_gateway[0].arn

  depends_on = [
    aws_api_gateway_stage.eligibility-signposting-api,
    aws_wafv2_web_acl.api_gateway
  ]
}

# CloudWatch Log Group for WAF logs
resource "aws_cloudwatch_log_group" "waf" {
  count             = local.waf_enabled ? 1 : 0
  name              = "aws-waf-logs-${local.workspace}-eligibility-signposting-api"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.waf_logs[0].arn

  tags = merge(
    local.tags,
    {
      Name        = "${local.workspace}-eligibility-signposting-api-waf-logs"
      Stack       = local.stack_name
      Environment = var.environment
    }
  )

  depends_on = [
    aws_kms_key_policy.waf_logs
  ]
}

# CloudWatch Logs resource policy to allow WAF to write logs
resource "aws_cloudwatch_log_resource_policy" "waf" {
  count       = local.waf_enabled ? 1 : 0
  policy_name = "${local.workspace}-waf-logging-policy"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSLogDeliveryWrite"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.waf[0].arn}:*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:*"
          }
        }
      },
      {
        Sid    = "AWSLogDeliveryAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "logs:GetLogDelivery"
        Resource = "*"
      }
    ]
  })
}

# KMS Key for WAF logs encryption
resource "aws_kms_key" "waf_logs" {
  count                   = local.waf_enabled ? 1 : 0
  description             = "KMS key for WAF CloudWatch logs encryption"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  tags = merge(
    local.tags,
    {
      Name        = "${local.workspace}-waf-logs-kms-key"
      Stack       = local.stack_name
      Environment = var.environment
    }
  )
}

resource "aws_kms_alias" "waf_logs" {
  count         = local.waf_enabled ? 1 : 0
  name          = "alias/${local.workspace}-waf-logs"
  target_key_id = aws_kms_key.waf_logs[0].key_id
}

resource "aws_kms_key_policy" "waf_logs" {
  count  = local.waf_enabled ? 1 : 0
  key_id = aws_kms_key.waf_logs[0].id
  policy = data.aws_iam_policy_document.waf_logs_kms[0].json
}

data "aws_iam_policy_document" "waf_logs_kms" {
  count = local.waf_enabled ? 1 : 0

  statement {
    sid    = "Enable IAM User Permissions"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions = [
      "kms:DescribeKey",
      "kms:GetKeyPolicy",
      "kms:GetKeyRotationStatus",
      "kms:ListAliases",
      "kms:ListGrants",
      "kms:ListKeyPolicies",
      "kms:ListResourceTags",
      "kms:PutKeyPolicy",
      "kms:ScheduleKeyDeletion",
      "kms:CancelKeyDeletion",
      "kms:UpdateKeyDescription",
      "kms:EnableKeyRotation",
      "kms:DisableKeyRotation",
      "kms:EnableKey",
      "kms:DisableKey",
      "kms:TagResource",
      "kms:UntagResource",
      "kms:CreateGrant",
      "kms:RevokeGrant",
      "kms:RetireGrant",
      "kms:ListGrants"
    ]
    resources = [aws_kms_key.waf_logs[0].arn]
  }

  statement {
    sid    = "Allow CloudWatch Logs"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["logs.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:CreateGrant",
      "kms:DescribeKey"
    ]
    resources = [aws_kms_key.waf_logs[0].arn]
    condition {
      test     = "ArnLike"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values = [
        "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/wafv2/*",
        "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:aws-wafv2-logs-*",
        "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:aws-waf-logs-*"
      ]
    }
  }
}

# Enable WAF logging to CloudWatch
resource "aws_wafv2_web_acl_logging_configuration" "api_gateway" {
  count                   = local.waf_enabled ? 1 : 0
  resource_arn            = aws_wafv2_web_acl.api_gateway[0].arn
  log_destination_configs = [aws_cloudwatch_log_group.waf[0].arn]

  # Redact sensitive data from logs
  redacted_fields {
    single_header {
      name = "authorization"
    }
  }

  redacted_fields {
    single_header {
      name = "cookie"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.waf,
    aws_wafv2_web_acl.api_gateway
  ]
}
