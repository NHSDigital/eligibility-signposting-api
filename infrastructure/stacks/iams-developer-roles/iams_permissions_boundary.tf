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
      "cloudwatch:DescribeAlarms",
      "cloudwatch:DescribeAlarmsForMetric",
      "cloudwatch:ListTagsForResource",
      "cloudwatch:TagResource",
      "cloudwatch:UntagResource",

      # DynamoDB - table management
      "dynamodb:DescribeTimeToLive",
      "dynamodb:DescribeTable",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:ListTables",
      "dynamodb:DeleteTable",
      "dynamodb:CreateTable",
      "dynamodb:TagResource",
      "dynamodb:ListTagsOfResource",

      # EC2 - networking infrastructure
      "ec2:Describe*",
      "ec2:ModifyVpcBlockPublicAccessOptions",
      "ec2:CreateTags",
      "ec2:CreateNetworkAclEntry",
      "ec2:CreateNetworkAcl",
      "ec2:AssociateRouteTable",
      "ec2:CreateVpc",
      "ec2:ModifyVpcAttribute",
      "ec2:DeleteVpc",
      "ec2:CreateRouteTable",
      "ec2:CreateSubnet",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:CreateSecurityGroup",
      "ec2:RevokeSecurityGroupEgress",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:AuthorizeSecurityGroupEgress",
      "ec2:CreateVpcEndpoint",
      "ec2:CreateFlowLogs",
      "ec2:ReplaceNetworkAclAssociation",
      "ec2:DeleteSecurityGroup",
      "ec2:DeleteNetworkAcl",

      # EventBridge - alarm forwarding to Splunk
      "events:PutRule",
      "events:PutTargets",
      "events:DeleteRule",
      "events:RemoveTargets",
      "events:DescribeRule",
      "events:ListTargetsByRule",
      "events:TagResource",
      "events:UntagResource",

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
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListRoles",
      "iam:ListPolicies",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListPolicyVersions",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:UpdateRole",
      "iam:PutRolePolicy",
      "iam:PutRolePermissionsBoundary",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:CreatePolicy",
      "iam:CreatePolicyVersion",
      "iam:TagRole",
      "iam:PassRole",
      "iam:TagPolicy",

      # KMS - encryption key management
      "kms:CreateKey",
      "kms:DescribeKey",
      "kms:Describe*",
      "kms:CreateAlias",
      "kms:ListKeys",
      "kms:List*",
      "kms:ListAliases",
      "kms:GetKeyPolicy",
      "kms:GetKeyPolicy*",
      "kms:GetKeyRotationStatus",
      "kms:DeleteAlias",
      "kms:UpdateKeyDescription",
      "kms:CreateGrant",
      "kms:TagResource",
      "kms:EnableKeyRotation",
      "kms:ScheduleKeyDeletion",
      "kms:PutKeyPolicy",
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey",

      # Lambda - function management
      "lambda:CreateFunction",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:DeleteFunction",
      "lambda:GetFunction",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionCodeSigningConfig",
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
      "lambda:GetProvisionedConcurrencyConfig",
      "lambda:GetLayerVersion",
      "lambda:PutProvisionedConcurrencyConfig",

      # CloudWatch Logs - log management
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:Describe*",
      "logs:ListTagsForResource",
      "logs:PutRetentionPolicy",
      "logs:AssociateKmsKey",
      "logs:PutMetricFilter",

      # S3 - bucket and object management
      "s3:GetLifecycleConfiguration",
      "s3:PutLifecycleConfiguration",
      "s3:GetBucketVersioning",
      "s3:GetEncryptionConfiguration",
      "s3:PutEncryptionConfiguration",
      "s3:GetBucketPolicy",
      "s3:GetBucketObjectLockConfiguration",
      "s3:GetBucketLogging",
      "s3:GetReplicationConfiguration",
      "s3:GetBucketWebsite",
      "s3:GetBucketRequestPayment",
      "s3:GetBucketCORS",
      "s3:GetBucketAcl",
      "s3:PutBucketAcl",
      "s3:GetAccelerateConfiguration",
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:GetBucketLocation",
      "s3:GetBucketPublicAccessBlock",
      "s3:PutBucketCORS",
      "s3:CreateBucket",
      "s3:DeleteBucket",
      "s3:GetBucketTagging",
      "s3:PutBucketPolicy",
      "s3:PutBucketVersioning",
      "s3:PutBucketPublicAccessBlock",
      "s3:PutBucketLogging",
      "s3:GetObjectTagging",
      "s3:PutObjectTagging",
      "s3:GetObjectVersion",

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
      "sns:ListSubscriptions",
      "sns:ListSubscriptionsByTopic",

      # SSM - parameter management
      "ssm:DescribeParameters",
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:ListTagsForResource",
      "ssm:PutParameter",
      "ssm:AddTagsToResource",

      #SQS - message management
      "sqs:SendMessage",
      "sqs:GetQueueAttributes",
      "sqs:listqueuetags",
      "sqs:createqueue"
    ]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.default_aws_region]
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
