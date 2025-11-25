# Common-only policy document (used in non-preprod)
data "aws_iam_policy_document" "permissions_boundary_common_only" {
  count = var.environment != "preprod" ? 1 : 0

  source_policy_documents = [
    data.aws_iam_policy_document.permissions_boundary_common.json
  ]
}

# Merged policy document (used only in preprod)
data "aws_iam_policy_document" "permissions_boundary_merged" {
  count = var.environment == "preprod" ? 1 : 0

  source_policy_documents = [
    data.aws_iam_policy_document.permissions_boundary_common.json,
    data.aws_iam_policy_document.permissions_boundary_preprod.json
  ]
}

# Final IAM policy resource
resource "aws_iam_policy" "permissions_boundary" {
  name        = "${local.stack_name}-${upper(var.project_name)}-PermissionsBoundary"
  description = var.environment == "preprod" ?
                  "Preprod-only permissions boundary additions" :
                  "Common permissions boundary"
  policy      = var.environment == "preprod" ?
                  data.aws_iam_policy_document.permissions_boundary_merged[0].json :
                  data.aws_iam_policy_document.permissions_boundary_common_only[0].json

  tags = merge(local.tags, { Stack = "iams-developer-roles" })
}
