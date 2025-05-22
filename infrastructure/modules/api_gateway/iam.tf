data "aws_iam_policy_document" "assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_gateway" {
  name               = "${var.workspace}-${var.api_gateway_name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "api_gateway_logging" {
  statement {
    sid    = "AllowCloudWatchLogging"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
      "logs:GetLogEvents",
      "logs:FilterLogEvents"
    ]
    resources = [
      aws_cloudwatch_log_group.api_gateway.arn,
      "${aws_cloudwatch_log_group.api_gateway.arn}:*"
    ]
  }
}

resource "aws_iam_policy" "api_gateway_logging" {
  name        = "${var.workspace}-${var.api_gateway_name}-api-gateway-logging-policy"
  description = "Policy to allow API Gateway push logs to Cloudwatch"
  policy      = data.aws_iam_policy_document.api_gateway_logging.json
}

resource "aws_iam_role_policy_attachment" "api_gateway_logging" {
  role       = aws_iam_role.api_gateway.name
  policy_arn = aws_iam_policy.api_gateway_logging.arn
}
