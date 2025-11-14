# Terraform State Management Policy
resource "aws_iam_policy" "terraform_state" {
  name        = "terraform-state-management"
  description = "Policy granting access to S3 bucket for Terraform state"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObject"
        ],
        Resource = [
          "${local.terraform_state_bucket_arn}",
          "${local.terraform_state_bucket_arn}/*"
        ]
      }
    ]
  })

  tags = merge(
    local.tags,
    {
      Name = "terraform-state-management"
    }
  )
}

# Lambda Management Policy
resource "aws_iam_policy" "lambda_management" {
  name        = "lambda-management"
  description = "Policy granting permissions to manage Lambda functions for this stack"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
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
          "lambda:GetFunction",
          "lambda:GetLayerVersion",
          "lambda:GetProvisionedConcurrencyConfig",
          "lambda:PutProvisionedConcurrencyConfig",
          "lambda:DeleteProvisionedConcurrencyConfig",
          "lambda:ListProvisionedConcurrencyConfigs",

        ],
        Resource = [
          "arn:aws:lambda:*:${data.aws_caller_identity.current.account_id}:function:eligibility_signposting_api",
          "arn:aws:lambda:*:${data.aws_caller_identity.current.account_id}:function:eligibility_signposting_api:*",
          "arn:aws:lambda:*:580247275435:layer:LambdaInsightsExtension:*"
        ]
      }
    ]
  })

  tags = merge(local.tags, { Name = "lambda-management" })
}

# DynamoDB Management Policy
resource "aws_iam_policy" "dynamodb_management" {
  name        = "dynamodb-management"
  description = "Policy granting permissions to manage DynamoDB tables for this stack"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = concat(
      [
        {
          Effect = "Allow",
          Action = [
            "dynamodb:DescribeTimeToLive",
            "dynamodb:DescribeTable",
            "dynamodb:DescribeContinuousBackups",
            "dynamodb:UpdateContinuousBackups",
            "dynamodb:ListTables",
            "dynamodb:DeleteTable",
            "dynamodb:CreateTable",
            "dynamodb:TagResource",
            "dynamodb:UntagResource",
            "dynamodb:ListTagsOfResource",
            "dynamodb:UpdateTable",
          ],
          Resource = [
            "arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/*eligibility-signposting-api-${var.environment}-eligibility_datastore"
          ]
        }
      ],
      # to create test users in preprod
      var.environment == "preprod" ? [
        {
          Effect = "Allow",
          Action = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:DeleteItem",
            "dynamodb:Scan",
            "dynamodb:BatchWriteItem",
            "dynamodb:Query"
          ],
          Resource = [
            "arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/*eligibility-signposting-api-${var.environment}-eligibility_datastore"
          ]
        }
      ] : []
    )
  })

  tags = merge(local.tags, { Name = "dynamodb-management" })
}

# S3 Management Policy
resource "aws_iam_policy" "s3_management" {
  name        = "s3-management"
  description = "Policy granting permissions to manage S3 buckets"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
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
          "s3:PutBucketTagging",
        ],
        Resource = [
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-rules",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-rules/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-audit",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-audit/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-rules-access-logs",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-rules-access-logs/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-audit-access-logs",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-audit-access-logs/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-truststore",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-truststore/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-truststore-access-logs",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-truststore-access-logs/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-splunk",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-splunk/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-splunk-access-logs",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-splunk-access-logs/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-artifacts",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-artifacts/*",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-artifacts-access-logs",
          "arn:aws:s3:::*eligibility-signposting-api-${var.environment}-eli-artifacts-access-logs/*",
        ]
      }
    ]
  })

  tags = merge(local.tags, { Name = "s3-management" })
}

# API Infrastructure Management Policy
resource "aws_iam_policy" "api_infrastructure" {
  #checkov:skip=CKV_AWS_288: Actions require read of wildcard resources to create VPCs, subnets, etc.
  #checkov:skip=CKV_AWS_290: Actions require write of wildcard resources to create VPCs, subnets, etc.
  #checkov:skip=CKV_AWS_355: Actions require wildcard access for creation of resources.
  name        = "api-infrastructure-management"
  description = "Policy granting permissions to manage API infrastructure"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:Describe*",
          "ssm:DescribeParameters",
          "ec2:Describe*",
          "ec2:DescribeVpcs",
          "ec2:ModifyVpcBlockPublicAccessOptions",
          # API Gateway domain and deployment
          "apigateway:*",
          # ACM for certs
          "acm:DescribeCertificate",
          "acm:GetCertificate",
          "acm:ListCertificates",
          # WAF v2 list operations
          "wafv2:ListWebACLs",
          "wafv2:ListTagsForResource"

        ],
        Resource = "*"
        #checkov:skip=CKV_AWS_289: Actions require wildcard resource
      },
      {
        Effect = "Allow",
        Action = [
          # CloudWatch Logs creation and management
          "logs:CreateLogGroup",
          "logs:DeleteLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          # CloudWatch Logs subscription filters for CSOC forwarding
          "logs:PutSubscriptionFilter",
          "logs:DeleteSubscriptionFilter",
          "logs:DescribeSubscriptionFilters"
        ],
        Resource = [
          # VPC Flow Logs
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/vpc/*",
          # Lambda function logs
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*",
          # API Gateway logs
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/apigateway/*",
          # Kinesis Firehose logs
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/kinesisfirehose/*",
          # WAF v2 logs (both naming conventions)
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/wafv2/*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:aws-wafv2-logs-*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          # CloudWatch Logs subscription to CSOC cross-account destination
          "logs:PutSubscriptionFilter"
        ],
        Resource = [
          # CSOC cross-account destination for API Gateway logs
          "arn:aws:logs:${var.default_aws_region}:693466633220:destination:api_gateway_log_destination"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          # IAM PassRole for specific service roles only
          "iam:PassRole"
        ],
        Resource = [
          # Lambda execution roles
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/eligibility_lambda-role*",
          # API Gateway CloudWatch logging role
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-api-gateway-*-role",
          # VPC Flow Logs role
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/vpc-flow-logs-role*",
          # EventBridge to Firehose role
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/eventbridge-firehose-role*",
          # Kinesis Firehose S3 backup roles
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*firehose*role*",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/splunk-firehose-assume-role*",
          # CSOC CloudWatch Logs subscription role
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-CWLogsSubscriptionRole"
        ],
        Condition = {
          StringEquals = {
            "iam:PassedToService" = [
              "lambda.amazonaws.com",
              "apigateway.amazonaws.com",
              "vpc-flow-logs.amazonaws.com",
              "events.amazonaws.com",
              "firehose.amazonaws.com",
              "logs.amazonaws.com"
            ]
          }
        }
      },
      {
        Effect = "Allow",
        Action = [
          # Cloudwatch permissions
          "logs:ListTagsForResource",
          "logs:PutRetentionPolicy",
          "logs:AssociateKmsKey",
          "logs:CreateLogGroup",
          "logs:PutMetricFilter",
          "logs:TagResource",

          # EC2 permissions
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "ec2:CreateNetworkAclEntry",
          "ec2:DeleteNetworkAclEntry",
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
          "ec2:UpdateSecurityGroupRuleDescriptionsEgress",

          # ssm
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:ListTagsForResource",
          "ssm:PutParameter",
          "ssm:AddTagsToResource",

          # acm
          "acm:ListTagsForCertificate",
          "acm:RequestCertificate",
          "acm:AddTagsToCertificate",
          "acm:ImportCertificate",

          # eventbridge
          "events:TagResource",
          "events:PutRule",
          "events:PutTargets",
          "events:DescribeRule",
          "events:ListTagsForResource",
          "events:DeleteRule",
          "events:ListTargetsByRule",
          "events:RemoveTargets",

          # WAF v2
          "wafv2:CreateWebACL",
          "wafv2:DeleteWebACL",
          "wafv2:GetWebACL",
          "wafv2:GetWebACLForResource",
          "wafv2:UpdateWebACL",
          "wafv2:TagResource",
          "wafv2:UntagResource",
          "wafv2:AssociateWebACL",
          "wafv2:DisassociateWebACL",
          "wafv2:PutLoggingConfiguration",
          "wafv2:GetLoggingConfiguration",
          "wafv2:DeleteLoggingConfiguration"
        ],


        Resource = [
          "arn:aws:ec2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:vpc/*",
          "arn:aws:ec2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:vpc-endpoint/*",
          "arn:aws:ec2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:vpc-flow-log/*",
          "arn:aws:ec2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:subnet/*",
          "arn:aws:ec2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:route-table/*",
          "arn:aws:ec2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:network-acl/*",
          "arn:aws:ec2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:security-group/*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/vpc/*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/apigateway/*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/kinesisfirehose/eligibility-signposting-api-${var.environment}-audit/*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:NHSDAudit_trail_log_group*",
          "arn:aws:ssm:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.environment}/*",
          "arn:aws:ssm:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:parameter/splunk/*",
          "arn:aws:acm:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:certificate/*",
          "arn:aws:events:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:rule/cloudwatch-alarm-state-change-to-splunk*",
          "arn:aws:wafv2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:regional/webacl/*",
          "arn:aws:wafv2:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:regional/managedruleset/*",
        ]
      },
    ]
  })

  tags = merge(
    local.tags,
    {
      Name = "api-infrastructure-management"
    }
  )
}

# Create KMS keys policy for GitHub Actions
resource "aws_iam_policy" "kms_creation" {
  #checkov:skip=CKV_AWS_290: Actions require wildcard resource (Creation and listing of keys)
  #checkov:skip=CKV_AWS_289: Actions require wildcard resource
  #checkov:skip=CKV_AWS_355: Actions require wildcard resource

  name        = "github-actions-kms-creation"
  description = "Policy allowing GitHub Actions to manage KMS keys"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          # Key creation and listing actions require wildcard resource
          "kms:CreateKey",
          "kms:CreateAlias",
          "kms:List*",
          "kms:ListAliases"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          # Key management actions on account-specific keys only
          "kms:DescribeKey",
          "kms:Describe*",
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
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey"
        ],
        Resource = [
          "arn:aws:kms:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:key/*",
          "arn:aws:kms:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:alias/*"
        ]
      }
    ]
  })

  tags = merge(local.tags, { Name = "github-actions-kms-creation" })
}


# IAM Management Policy
resource "aws_iam_policy" "iam_management" {
  name        = "iam-management"
  description = "Policy granting permissions to manage only project-specific IAM roles and policies"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "iam:Get*",
          "iam:GetPolicy*",
          "iam:GetRole*",
          "iam:List*",
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:UpdateRole",
          "iam:UpdateAssumeRolePolicy",
          "iam:PutRolePolicy",
          "iam:PutRolePermissionsBoundary",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:CreatePolicy",
          "iam:CreatePolicyVersion",
          "iam:DeletePolicy",
          "iam:DeletePolicyVersion",
          "iam:TagRole",
          "iam:PassRole",
          "iam:TagPolicy",
          "iam:UntagPolicy",
        ],
        Resource = [
          # Lambda role
          "arn:aws:iam::*:role/eligibility_lambda-role*",
          # Kinesis Role
          "arn:aws:iam::*:role/eligibility_audit_firehose-role*",
          # API Gateway role
          "arn:aws:iam::*:role/*-api-gateway-*-role",
          # External write role
          "arn:aws:iam::*:role/eligibility-signposting-api-*-external-write-role",
          # CSOC CloudWatch Logs subscription role
          "arn:aws:iam::*:role/*-CWLogsSubscriptionRole",
          # Project policies
          "arn:aws:iam::*:policy/*api-gateway-logging-policy",
          "arn:aws:iam::*:policy/*PermissionsBoundary",
          "arn:aws:iam::*:policy/*PutSubscriptionFilterPolicy",
          "arn:aws:iam::*:policy/*CWLogsToCSOCDestinationPolicy",
          # VPC flow logs role
          "arn:aws:iam::*:role/vpc-flow-logs-role",
          # API role
          "arn:aws:iam::*:role/*eligibility-signposting-api-role",
          # Kinesis firehose role
          "arn:aws:iam::*:role/eligibility_audit_firehose-role*",
          # Eventbridge to firehose role
          "arn:aws:iam::*:role/*-eventbridge-to-firehose-role*",
          # Firehose splunk role
          "arn:aws:iam::*:role/splunk-firehose-role"
        ]
      }
    ]
  })
  tags = merge(local.tags, { Name = "iam-management" })
}

# Assume role policy document for GitHub Actions
data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    sid     = "OidcAssumeRoleWithWebIdentity"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type = "Federated"
      identifiers = [
        aws_iam_openid_connect_provider.github.arn
      ]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_org}/${var.github_repo}:*"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "firehose_readonly" {
  name        = "firehose-describe-access"
  description = "Allow GitHub Actions to describe Firehose delivery stream"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
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
          "firehose:StopDeliveryStreamEncryption"
        ]
        Resource = [
          "arn:aws:firehose:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:deliverystream/eligibility-signposting-api*",
          "arn:aws:firehose:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:deliverystream/splunk-alarm-events*"
        ]
      }
    ]
  })
  tags = merge(local.tags, { Name = "firehose-describe-access" })
}

resource "aws_iam_policy" "cloudwatch_management" {
  name        = "cloudwatch-management"
  description = "Allow GitHub Actions to manage CloudWatch logs, alarms, and SNS topics"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:ListTagsForResource",
          "logs:DescribeLogGroups",
          "logs:DeleteLogGroup",
          "logs:PutRetentionPolicy",
          "logs:TagResource",
          "logs:UntagResource",

          "cloudwatch:PutMetricAlarm",
          "cloudwatch:DeleteAlarms",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:DescribeAlarmsForMetric",
          "cloudwatch:ListTagsForResource",
          "cloudwatch:TagResource",
          "cloudwatch:UntagResource",

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
          "sns:ListSubscriptionsByTopic"
        ],
        Resource = [
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/kinesisfirehose/*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/wafv2/*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:aws-wafv2-logs-*",
          "arn:aws:cloudwatch:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:alarm:*",
          "arn:aws:sns:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:cloudwatch-security-alarms*",
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/apigateway/default-eligibility-signposting-api*",
        ]
      }
    ]
  })

  tags = merge(local.tags, { Name = "cloudwatch-management" })
}

# Attach the policies to the role
resource "aws_iam_role_policy_attachment" "terraform_state" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.terraform_state.arn
}

resource "aws_iam_role_policy_attachment" "api_infrastructure" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.api_infrastructure.arn
}

resource "aws_iam_role_policy_attachment" "lambda_management" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.lambda_management.arn
}

resource "aws_iam_role_policy_attachment" "dynamodb_management" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.dynamodb_management.arn
}

resource "aws_iam_role_policy_attachment" "s3_management" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.s3_management.arn
}

resource "aws_iam_role_policy_attachment" "kms_creation" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.kms_creation.arn
}

resource "aws_iam_role_policy_attachment" "iam_management" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.iam_management.arn
}

resource "aws_iam_role_policy_attachment" "firehose_readonly_attach" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.firehose_readonly.arn
}

resource "aws_iam_role_policy_attachment" "cloudwatch_management" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.cloudwatch_management.arn
}
