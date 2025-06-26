module "eligibility_audit_firehose_delivery_stream" {
  source                              = "../../modules/kinesis_firehose"
  audit_firehose_delivery_stream_name = "audit_stream_to_s3"
  audit_firehose_role_arn             = aws_iam_role.eligibility_audit_firehose_role.arn
  s3_audit_bucket_arn                 = module.s3_audit_bucket.storage_bucket_arn
  environment                         = local.environment
  stack_name                          = local.stack_name
  workspace                           = local.workspace
  tags                                = local.tags
  kinesis_cloud_watch_log_group_name  = aws_cloudwatch_log_group.firehose_audit.name
  kinesis_cloud_watch_log_stream      = aws_cloudwatch_log_stream.firehose_audit_stream.name
}
