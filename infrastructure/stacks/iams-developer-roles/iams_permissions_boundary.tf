# Policy document for Permissions boundary
data "aws_iam_policy_document" "permissions_boundary" {
  #checkov:skip=CKV2_AWS_40: Ensure AWS IAM policy does not allow full IAM privileges
  statement {
    sid    = "RestrictRegion"
    effect = "Allow"

    actions = [
      # ACM - only specific actions needed for certificate management
      "acm:DescribeCertificate",
      "acm:GetCertificate",
      "acm:ListCertificates",
      "acm:ListTagsForCertificate",
      "acm:RequestCertificate",
      "acm:AddTagsToCertificate",
      "acm:ImportCertificate",

      # API Gateway - specific actions for deployment
      "apigateway:*",

      # CloudWatch - monitoring and alarms
      "cloudwatch:PutMetricAlarm",
      "cloudwatch:DeleteAlarms",
      "cloudwatch:DescribeAlarms*",
      "cloudwatch:ListTagsForResource",
      "cloudwatch:TagResource",
      "cloudwatch:UntagResource",
      "cloudwatch:GetDashboard",
      "cloudwatch:GetMetricWidgetImage",

      # DynamoDB - table management
      "dynamodb:Describe*",
      "dynamodb:ListTables",
      "dynamodb:DeleteTable",
      "dynamodb:CreateTable",
      "dynamodb:TagResource",
      "dynamodb:UntagResource",
      "dynamodb:ListTagsOfResource",
      "dynamodb:UpdateTable",
      "dynamodb:UpdateContinuousBackups",

      # EC2 - networking infrastructure
      "ec2:Describe*",
      "ec2:ModifyVpcBlockPublicAccessOptions",
      "ec2:CreateTags",
      "ec2:DeleteTags",
      "ec2:CreateNetworkAcl*",
      "ec2:DeleteNetworkAcl*",
      "ec2:AssociateRouteTable",
      "ec2:CreateVpc*",
      "ec2:ModifyVpcAttribute",
      "ec2:DeleteVpc",
      "ec2:CreateRouteTable",
      "ec2:CreateSubnet",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:CreateSecurityGroup",
      "ec2:RevokeSecurityGroupEgress",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:AuthorizeSecurityGroupEgress",
      "ec2:CreateFlowLogs",
      "ec2:ReplaceNetworkAclAssociation",
      "ec2:DeleteSecurityGroup",
      "ec2:UpdateSecurityGroupRuleDescriptionsEgress",

      # EventBridge - alarm forwarding to Splunk
      "events:PutRule",
      "events:PutTargets",
      "events:DeleteRule",
      "events:RemoveTargets",
      "events:DescribeRule",
      "events:ListTargetsByRule",
      "events:TagResource",
      "events:UntagResource",
      "events:ListTagsForResource",

      # Kinesis Firehose - log streaming
      "firehose:CreateDeliveryStream",
      "firehose:DeleteDeliveryStream",
      "firehose:DescribeDeliveryStream",
      "firehose:UpdateDestination",
      "firehose:PutRecord",
      "firehose:PutRecordBatch",
      "firehose:TagDeliveryStream",
      "firehose:ListTagsForDeliveryStream",
      "firehose:UntagDeliveryStream",
      "firehose:StartDeliveryStreamEncryption",
      "firehose:StopDeliveryStreamEncryption",

      # IAM - specific role and policy management
      "iam:GetRole*",
      "iam:GetPolicy*",
      "iam:ListRole*",
      "iam:ListPolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListPolicyVersions",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:UpdateRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:PutRolePolicy",
      "iam:PutRolePermissionsBoundary",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:CreatePolicy*",
      "iam:DeletePolicy*",
      "iam:TagRole",
      "iam:UntagPolicy",
      "iam:PassRole",
      "iam:TagPolicy",
      "iam:CreateServiceLinkedRole",

      # KMS - encryption key management
      "kms:CreateKey",
      "kms:Describe*",
      "kms:CreateAlias",
      "kms:List*",
      "kms:GetKeyPolicy*",
      "kms:GetKeyRotationStatus",
      "kms:DeleteAlias",
      "kms:UpdateKeyDescription",
      "kms:CreateGrant",
      "kms:TagResource",
      "kms:UntagResource",
      "kms:EnableKeyRotation",
      "kms:ScheduleKeyDeletion",
      "kms:PutKeyPolicy",
      "kms:Encrypt",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey",

      # Lambda - function management
      "lambda:CreateFunction",
      "lambda:UpdateFunction*",
      "lambda:DeleteFunction",
      "lambda:GetFunction*",
      "lambda:ListVersionsByFunction",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:ListTags",
      "lambda:PublishVersion",
      "lambda:CreateAlias",
      "lambda:UpdateAlias",
      "lambda:DeleteAlias",
      "lambda:ListAliases",
      "lambda:AddPermission",
      "lambda:RemovePermission",
      "lambda:GetPolicy",
      "lambda:GetAlias",
      "lambda:GetLayerVersion",
      "lambda:GetProvisionedConcurrencyConfig",
      "lambda:PutProvisionedConcurrencyConfig",
      "lambda:DeleteProvisionedConcurrencyConfig",
      "lambda:ListProvisionedConcurrencyConfigs",
      "lambda:PutFunctionConcurrency",

      # CloudWatch Logs - log management
      "logs:*",

      # S3 - bucket and object management
      "s3:GetLifecycleConfiguration",
      "s3:PutLifecycleConfiguration",
      "s3:GetEncryptionConfiguration",
      "s3:PutEncryptionConfiguration",
      "s3:GetReplicationConfiguration",
      "s3:GetAccelerateConfiguration",
      "s3:ListBucket",
      "s3:GetObject*",
      "s3:PutObject*",
      "s3:DeleteObject",
      "s3:GetBucket*",
      "s3:CreateBucket",
      "s3:DeleteBucket",
      "s3:PutBucket*",

      # SNS - notification management
      "sns:CreateTopic",
      "sns:DeleteTopic",
      "sns:GetTopicAttributes",
      "sns:SetTopicAttributes",
      "sns:ListTopics",
      "sns:ListTagsForResource",
      "sns:TagResource",
      "sns:UntagResource",
      "sns:Subscribe",
      "sns:Unsubscribe",
      "sns:ListSubscriptions*",
      "sns:GetSubscriptionAttributes",

      # SSM - parameter management
      "ssm:DescribeParameters",
      "ssm:GetParameter*",
      "ssm:ListTagsForResource",
      "ssm:PutParameter",
      "ssm:AddTagsToResource",
      "ssm:DeleteParameter",

      # WAFv2 - web application firewall management
      "wafv2:CreateWebACL",
      "wafv2:DeleteWebACL",
      "wafv2:GetWebACL*",
      "wafv2:UpdateWebACL",
      "wafv2:ListWebACLs",
      "wafv2:TagResource",
      "wafv2:UntagResource",
      "wafv2:ListTagsForResource",
      "wafv2:AssociateWebACL",
      "wafv2:DisassociateWebACL",
      "wafv2:PutLoggingConfiguration",
      "wafv2:GetLoggingConfiguration",
      "wafv2:DeleteLoggingConfiguration",

      # Secret Manager
      "secretsmanager:*",

      # State Machine management
      "states:DescribeStateMachine",
      "states:ListStateMachineVersions",
      "states:ListTagsForResource",
      "states:ValidateStateMachineDefinition",
      "states:CreateStateMachine",
      "states:TagResource",
      "states:UpdateStateMachine",
    ]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.default_aws_region]
    }
  }
  # Environment-specific actions
  dynamic "statement" {
    for_each = var.environment == "preprod" ? [1] : []
    content {
      sid    = "AllowPreprodDynamoDBItemOps"
      effect = "Allow"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:BatchWriteItem",
        "dynamodb:Query"
      ]
      resources = ["*"]
    }
  }
  # Allow access to IAM actions for us-east-1 region only
  statement {
    sid       = "AllowIamActionsInUsEast1"
    effect    = "Allow"
    actions   = ["iam:*"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = ["us-east-1"]
    }
  }

  statement {
    sid       = "DenyPrivEsculationViaIamRoles"
    effect    = "Deny"
    actions   = ["iam:*"]
    resources = ["*"]
    condition {
      test     = "ArnLike"
      variable = "iam:PolicyARN"
      values   = ["arn:aws:iam::*:policy/${upper(var.project_name)}-*"]
    }
  }

  statement {
    sid       = "DenyPrivEsculationViaIamProfiles"
    effect    = "Deny"
    actions   = ["iam:*"]
    resources = ["arn:aws:iam::*:role/${upper(var.project_name)}-*"]
  }
}

# Permissions Boundary policy
resource "aws_iam_policy" "permissions_boundary" {
  name        = "${local.stack_name}-${upper(var.project_name)}-PermissionsBoundary"
  description = "Allows access to AWS services in the regions the client uses only"
  policy      = data.aws_iam_policy_document.permissions_boundary.json

  tags = merge(
    local.tags,
    {
      Stack = "iams-developer-roles"
    }
  )
}
