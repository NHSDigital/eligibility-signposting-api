module "eligibility_audit_firehose_delivery_stream" {
  source                              = "../../modules/kinesis_firehose"
  audit_firehose_delivery_stream_name = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"}eligibility_audit_stream"
  audit_firehose_role_arn             = aws_iam_role.eligibility_audit_firehose_role.arn
  s3_audit_bucket_arn                 = module.s3_audit_bucket.storage_bucket_arn
}
