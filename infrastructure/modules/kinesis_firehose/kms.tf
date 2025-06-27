resource "aws_kms_key" "firehose_cmk" {
  description             = "KMS key for Kinesis Firehose encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}


resource "aws_kms_alias" "firehose_cmk" {
  name          = "alias/kinesis-firehose-${var.environment}"
  target_key_id = aws_kms_key.firehose_cmk.key_id
}

