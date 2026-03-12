resource "aws_iam_user" "tableau_service" {
  name = "tableau-athena-service-account"
}

resource "time_rotating" "athena_key_rotation" {
  rotation_days = 90
}

resource "aws_iam_access_key" "tableau_key" {
  user = aws_iam_user.tableau_service.name

  lifecycle {
    replace_triggered_by = [time_rotating.athena_key_rotation]
  }
}

resource "aws_iam_user_policy" "tableau_athena_policy" {
  name = "TableauAthenaAccess"
  user = aws_iam_user.tableau_service.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Athena Query Actions
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
        # Metadata Discovery
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetDatabases"
        ]
        Resource = [
          "arn:aws:glue:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:database/elid_db",
          "arn:aws:glue:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:table/elid_db/cohort_metrics"
        ]
      },
      {
        # 3. Data Access (Your specific S3 bucket)
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
        # Athena Results - Staging Directory
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
