# IAM management policy – scoped to project resources
resource "aws_iam_policy" "iam_bootstrap_iam_management" {
  name        = "${upper(var.project_name)}-iam-bootstrap-iam-management"
  description = "Allows the IAM bootstrap role to manage project IAM resources"
  path        = "/service-policies/"

  policy = data.aws_iam_policy_document.iam_bootstrap_iam_management.json

  tags = merge(local.tags, { Name = "${upper(var.project_name)}-iam-bootstrap-iam-management" })
}

data "aws_iam_policy_document" "iam_bootstrap_iam_management" {
  # Full IAM access for project-scoped resources
  statement {
    sid    = "IamManageProjectResources"
    effect = "Allow"
    actions = [
      "iam:GetRole*",
      "iam:GetPolicy*",
      "iam:ListRole*",
      "iam:ListPolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListPolicyVersions",
      "iam:ListPolicyTags",
      "iam:ListOpenIDConnectProviders",
      "iam:ListOpenIDConnectProviderTags",
      "iam:GetOpenIDConnectProvider",
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
      "iam:SetDefaultPolicyVersion",
      "iam:TagRole",
      "iam:TagPolicy",
      "iam:UntagRole",
      "iam:UntagPolicy",
      "iam:PassRole",
      "iam:TagOpenIDConnectProvider",
      "iam:UntagOpenIDConnectProvider",
      "iam:CreateOpenIDConnectProvider",
      "iam:DeleteOpenIDConnectProvider",
      "iam:UpdateOpenIDConnectProviderThumbprint",
      "iam:AddClientIDToOpenIDConnectProvider",
      "iam:RemoveClientIDFromOpenIDConnectProvider",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/service-roles/github-actions-api-deployment-role",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/service-roles/github-actions-iam-bootstrap-role",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-terraform-developer-role",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/terraform-developer-role",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${upper(var.project_name)}-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${lower(var.project_name)}-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/service-policies/*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${local.stack_name}-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com",
    ]
  }

  # Read-only IAM access for Terraform plan/discovery
  statement {
    sid    = "IamReadOnly"
    effect = "Allow"
    actions = [
      "iam:Get*",
      "iam:List*",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/*",
    ]
  }

  # DENY: Prevent modifying the bootstrap role itself
  statement {
    sid    = "DenySelfModification"
    effect = "Deny"
    actions = [
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:UpdateAssumeRolePolicy",
      "iam:PutRolePermissionsBoundary",
      "iam:DeleteRolePermissionsBoundary",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/service-roles/github-actions-iam-bootstrap-role",
    ]
  }

  # DENY: Prevent modifying the bootstrap permissions boundary
  statement {
    sid    = "DenyBootstrapBoundaryModification"
    effect = "Deny"
    actions = [
      "iam:CreatePolicyVersion",
      "iam:DeletePolicy",
      "iam:DeletePolicyVersion",
      "iam:SetDefaultPolicyVersion",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${lower(var.project_name)}-iam-bootstrap-permissions-boundary",
    ]
  }
}

# Terraform state management policy
resource "aws_iam_policy" "iam_bootstrap_terraform_state" {
  name        = "${upper(var.project_name)}-iam-bootstrap-terraform-state"
  description = "Allows the IAM bootstrap role to manage Terraform state for the iams-developer-roles stack"
  path        = "/service-policies/"

  policy = data.aws_iam_policy_document.iam_bootstrap_terraform_state.json

  tags = merge(local.tags, { Name = "${upper(var.project_name)}-iam-bootstrap-terraform-state" })
}

data "aws_iam_policy_document" "iam_bootstrap_terraform_state" {
  # S3 state bucket access
  statement {
    sid    = "TerraformStateS3Access"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${local.terraform_state_bucket_arn}",
      "${local.terraform_state_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy_attachment" "iam_bootstrap_iam_management" {
  role       = aws_iam_role.github_actions_iam_bootstrap.name
  policy_arn = aws_iam_policy.iam_bootstrap_iam_management.arn
}

resource "aws_iam_role_policy_attachment" "iam_bootstrap_terraform_state" {
  role       = aws_iam_role.github_actions_iam_bootstrap.name
  policy_arn = aws_iam_policy.iam_bootstrap_terraform_state.arn
}
