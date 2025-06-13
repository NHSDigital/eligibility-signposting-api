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
          "s3:DeleteObject"
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
          "lambda:GetPolicy"
        ],
        Resource = [
          "arn:aws:lambda:*:${data.aws_caller_identity.current.account_id}:function:*eligibility_signposting_api"
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
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:DescribeTimeToLive",
          "dynamodb:DescribeTable",
          "dynamodb:DescribeContinuousBackups",
          "dynamodb:ListTables",
          "dynamodb:DeleteTable",
          "dynamodb:CreateTable",
          "dynamodb:TagResource",
          "dynamodb:ListTagsOfResource",
        ],
        Resource = [
          "arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/*eligibility-signposting-api-${var.environment}-eligibility_datastore"
        ]
      }
    ]
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
        ]
      }
    ]
  })

  tags = merge(local.tags, { Name = "s3-management" })
}

# API Infrastructure Management Policy
resource "aws_iam_policy" "api_infrastructure" {
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
          "acm:ListCertificates",
          "apigateway:*",
          "iam:PassRole",
        ],
        Resource = "*"
        #checkov:skip=CKV_AWS_289: Actions require wildcard resource
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

          # EC2 permissions
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

          # ssm
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:ListTagsForResource",
          "ssm:PutParameter",
          "ssm:AddTagsToResource",

          # acm
          "acm:DescribeCertificate",
          "acm:GetCertificate",
          "acm:ListTagsForCertificate",
          "acm:RequestCertificate",
          "acm:AddTagsToCertificate",
          "acm:ImportCertificate",
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
          "arn:aws:logs:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:log-group:NHSDAudit_trail_log_group*",
          "arn:aws:ssm:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.environment}/*",
          "arn:aws:acm:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:certificate/*",
        ]
      }
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
  name        = "github-actions-kms-creation"
  description = "Policy allowing GitHub Actions to manage KMS keys"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "kms:CreateKey",
          "kms:CreateAlias",
          "kms:List*",
          "kms:ListAliases",
        ],
        Resource = "*"
        #checkov:skip=CKV_AWS_289: Actions require wildcard resource
      },
      {
        Effect = "Allow",
        Action = [
          "kms:Describe*",
          "kms:GetKeyPolicy*",
          "kms:GetKeyRotationStatus",
          "kms:Decrypt*",
          "kms:DeleteAlias",
          "kms:UpdateKeyDescription",
          "kms:CreateGrant",
          "kms:TagResource",
          "kms:EnableKeyRotation",
          "kms:ScheduleKeyDeletion",
          "kms:PutKeyPolicy",
          "kms:Encrypt",
          "kms:TagResource",
          "kms:GenerateDataKey",
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
          "iam:PutRolePolicy",
          "iam:PutRolePermissionsBoundary",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:CreatePolicy",
          "iam:CreatePolicyVersion",
          "iam:TagRole",
          "iam:PassRole",
          "iam:TagPolicy",
        ],
        Resource = [
          # Lambda role
          "arn:aws:iam::*:role/eligibility_lambda-role*",
          # API Gateway role
          "arn:aws:iam::*:role/*-api-gateway-*-role",
          # External write role
          "arn:aws:iam::*:role/eligibility-signposting-api-*-external-write-role",
          # Project policies
          "arn:aws:iam::*:policy/*api-gateway-logging-policy",
          "arn:aws:iam::*:policy/*PermissionsBoundary",
          # VPC flow logs role
          "arn:aws:iam::*:role/vpc-flow-logs-role",
          # API role
          "arn:aws:iam::*:role/*eligibility-signposting-api-role"
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
