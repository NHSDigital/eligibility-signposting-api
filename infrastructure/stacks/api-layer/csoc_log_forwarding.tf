# CSOC Log Forwarding Configuration
# This file implements the requirements for forwarding API Gateway logs to CSOC
# Based on https://nhsd-confluence.digital.nhs.uk/spaces/CCEP/pages/407374909/API+Gateway+Access+Logs
#
# This implementation uses the existing API Gateway log group and adds a subscription
# filter to forward logs to CSOC, avoiding the need to create a duplicate log group.

# IAM Role for Cross Account Log Subscriptions
# This role allows CloudWatch Logs service to assume a role for cross-account log delivery
data "aws_iam_policy_document" "cwl_subscription_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["logs.${var.default_aws_region}.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "aws:SourceArn"
      values   = ["${module.eligibility_signposting_api_gateway.cloudwatch_destination_arn}:*"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "cwl_subscription_role" {
  name               = "${var.environment}-${local.workspace}-CWLogsSubscriptionRole"
  description        = "IAM role for CloudWatch Logs subscription filter to forward logs to CSOC"
  assume_role_policy = data.aws_iam_policy_document.cwl_subscription_assume_role.json

  tags = merge(
    local.tags,
    {
      Name    = "${var.environment}-${local.workspace}-CWLogsSubscriptionRole"
      Purpose = "CSOC log forwarding"
    }
  )
}

# IAM policy to allow PutSubscriptionFilter on the existing API Gateway log group and CSOC destination
data "aws_iam_policy_document" "put_subscription_filter" {
  statement {
    sid    = "AllowPutAPIGSubFilter"
    effect = "Allow"
    actions = [
      "logs:PutSubscriptionFilter"
    ]
    resources = [
      "${module.eligibility_signposting_api_gateway.cloudwatch_destination_arn}:*",
      "arn:aws:logs:${var.default_aws_region}:693466633220:destination:api_gateway_log_destination"
    ]
  }
}

resource "aws_iam_policy" "put_subscription_filter" {
  name        = "${var.environment}-${local.workspace}-PutSubscriptionFilterPolicy"
  description = "Policy to allow creating subscription filters for CSOC log forwarding"
  policy      = data.aws_iam_policy_document.put_subscription_filter.json

  tags = merge(
    local.tags,
    {
      Name    = "${var.environment}-${local.workspace}-PutSubscriptionFilterPolicy"
      Purpose = "CSOC log forwarding"
    }
  )
}

# Attach the policy to the subscription role
resource "aws_iam_role_policy_attachment" "put_subscription_filter" {
  role       = aws_iam_role.cwl_subscription_role.name
  policy_arn = aws_iam_policy.put_subscription_filter.arn
}

# Create the subscription filter to forward logs to CSOC
# This forwards all logs from the existing API Gateway log group to the CSOC destination
# Note: A log group can have up to 2 subscription filters
resource "aws_cloudwatch_log_subscription_filter" "csoc_forwarding" {
  name            = "${local.workspace}-csoc-subscription"
  log_group_name  = split(":", module.eligibility_signposting_api_gateway.cloudwatch_destination_arn)[6]
  filter_pattern  = "" # Empty filter pattern captures all log events
  destination_arn = "arn:aws:logs:${var.default_aws_region}:693466633220:destination:api_gateway_log_destination"
  role_arn        = aws_iam_role.cwl_subscription_role.arn

  depends_on = [
    module.eligibility_signposting_api_gateway,
    aws_iam_role.cwl_subscription_role,
    aws_iam_role_policy_attachment.put_subscription_filter
  ]
}
