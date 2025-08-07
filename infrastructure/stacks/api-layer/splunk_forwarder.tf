module "splunk_forwarder" {
  source = "../../modules/splunk_forwarder"

  splunk_hec_endpoint           = data.aws_ssm_parameter.splunk_hec_endpoint.value
  splunk_hec_token              = data.aws_ssm_parameter.splunk_hec_token.value
  splunk_firehose_s3_role_arn   = aws_iam_role.splunk_firehose_assume_role.arn
  splunk_firehose_s3_backup_arn = module.s3_firehose_backup_bucket.storage_bucket_arn
}
