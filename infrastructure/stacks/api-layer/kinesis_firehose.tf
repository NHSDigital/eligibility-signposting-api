module "eligibility_audit_firehose_delivery_stream" {
  source                                = "../../modules/kinesis_firehose"
  audit_firehose_delivery_stream_name   = "audit_stream_to_s3"
  audit_firehose_role                   = aws_iam_role.eligibility_audit_firehose_role
  s3_audit_bucket_arn                   = module.s3_audit_bucket.storage_bucket_arn
  environment                           = local.environment
  stack_name                            = local.stack_name
  workspace                             = local.workspace
  tags                                  = local.tags
  firehose_cloud_watch_log_group_name   = aws_cloudwatch_log_group.firehose_audit.name
  firehose_cloud_watch_log_stream       = aws_cloudwatch_log_stream.firehose_audit_stream.name
  eligibility_lambda_role_arn           = aws_iam_role.eligibility_lambda_role.arn
  kinesis_source_stream_arn             = aws_kinesis_stream.kinesis_source_stream.arn

  depends_on = [
    aws_iam_role_policy.kinesis_firehose_read_policy,
    aws_iam_role_policy.firehose_kinesis_source_kms_policy,
    aws_iam_role_policy.kinesis_firehose_s3_write_policy,
    aws_iam_role_policy.kinesis_firehose_logs_policy,
  ]
}
