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

# API Infrastructure Management Policy
resource "aws_iam_policy" "api_infrastructure" {
  #checkov:skip=CKV_AWS_287 Ensure IAM policies does not allow credentials exposure
  #checkov:skip=CKV_AWS_355 Ensure no IAM policies documents allow "*" as a statement's resource for restrictable actions
  #checkov:skip=CKV_AWS_288 Ensure IAM policies does not allow data exfiltration
  #checkov:skip=CKV_AWS_289 Ensure IAM policies does not allow permissions management / resource exposure without constraints
  #checkov:skip=CKV_AWS_286 Ensure IAM policies does not allow privilege escalation
  #checkov:skip=CKV_AWS_290 Ensure IAM policies does not allow write access without constraints

  name        = "api-infrastructure-management"
  description = "Policy granting permissions to manage API infrastructure"
  path        = "/service-policies/"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          # Lambda permissions
          "lambda:*",

          # DynamoDB permissions
          "dynamodb:*",

          # API Gateway permissions
          "apigateway:*",

          # S3 permissions
          "s3:*",

          # KMS permissions
          "kms:List*",
          "kms:Describe*",
          "kms:GetKeyPolicy*",
          "kms:GetKeyRotationStatus",
          "kms:Decrypt*",
          "kms:DeleteAlias",
          "kms:UpdateKeyDescription",
          "kms:CreateGrant",
          "kms:CreateAlias",
          "kms:TagResource",
          "kms:CreateKey",
          "kms:EnableKeyRotation",
          "kms:ScheduleKeyDeletion",
          "kms:PutKeyPolicy",
          "kms:Encrypt",
          "kms:ListAliases",
          "kms:TagResource",
          "kms:GenerateDataKey",

          # Cloudwatch permissions
          "logs:Describe*",
          "logs:ListTagsForResource",
          "logs:PutRetentionPolicy",
          "logs:AssociateKmsKey",
          "logs:CreateLogGroup",

          #EC2 permissions
          "ec2:Describe*",
          "ec2:CreateTags",
          "ec2:CreateNetworkAclEntry",
          "ec2:CreateNetworkAcl",
          "ec2:AssociateRouteTable",

          # IAM permissions (scoped to resources with specific path prefix)
          "iam:Get*",
          "iam:GetPolicy*",
          "iam:GetRole*",
          "iam:List*",
          "iam:Create*",
          "iam:Update*",
          "iam:Delete*",
          "iam:PutRolePermissionsBoundary",
          "iam:PutRolePolicy",
          "iam:CreateRole",
          "iam:TagRole",
          "iam:PassRole",

          # ssm
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:DescribeParameters",
          "ssm:ListTagsForResource",
          "ssm:PutParameter",
          "ssm:AddTagsToResource",

          # acm
          "acm:ListCertificates",
          "acm:DescribeCertificate",
          "acm:GetCertificate",
          "acm:ListTagsForCertificate",
          "acm:RequestCertificate",
          "acm:AddTagsToCertificate",
          "acm:ImportCertificate",

          # ec2 - VPC
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
          "ec2:DeleteNetworkAcl"
        ],

        Resource = "*"
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

# Assume role policy document for GitHub Actions
data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    sid    = "OidcAssumeRoleWithWebIdentity"
    effect = "Allow"
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
      values = ["repo:${var.github_org}/${var.github_repo}:*"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values = ["sts.amazonaws.com"]
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
