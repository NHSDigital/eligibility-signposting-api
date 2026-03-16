resource "aws_iam_openid_connect_provider" "tableau_idp" {
  url             = "https://your-idp-domain.com"
  client_id_list  = ["your-client-id"]
  thumbprint_list = ["a01152157448772d219323f136284e963b53b843"]
}

data "aws_iam_policy_document" "tableau_trust_policy" {
  statement {
    sid     = "AllowAthenaJwtPlugin"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.tableau_idp.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.tableau_idp.url, "https://", "")}:aud"
      values   = ["your-client-id"]
    }

    condition {
      test     = "StringEquals"
      variable = "sts:RoleSessionName"
      values   = ["AthenaJWT"]
    }
  }
}

resource "aws_iam_role" "tableau_athena_role" {
  name                 = "tableau-athena-federated-role"
  assume_role_policy   = data.aws_iam_policy_document.tableau_trust_policy.json
}

resource "aws_iam_role_policy" "tableau_athena_policy" {
  name = "TableauAthenaAccess"
  role = aws_iam_role.tableau_athena_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        sid    = "AthenaQueryActions"
        Effect = "Allow"
        Action = [
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StartQueryExecution",
          "athena:GetWorkGroup",
          "athena:StopQueryExecution",
          "athena:GetDataCatalog"
        ]
        Resource = [
          "arn:aws:athena:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:workgroup/primary"
        ]
      },
      {
        sid    = "GlueMetadataDiscovery"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetDatabases"
        ]
        Resource = [
          "arn:aws:glue:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:database/elid_dq",
          "arn:aws:glue:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:table/elid_dq/cohort_metrics"
        ]
      },
      {
        sid    = "DataBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${module.s3_dq_metrics_bucket.storage_bucket_name}",
          "arn:aws:s3:::${module.s3_dq_metrics_bucket.storage_bucket_name}/*"
        ]
      },
      {
        sid    = "AthenaResultsStaging"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::${module.s3_athena_dq_query_bucket.storage_bucket_name}",
          "arn:aws:s3:::${module.s3_athena_dq_query_bucket.storage_bucket_name}/*"
        ]
      }
    ]
  })
}
