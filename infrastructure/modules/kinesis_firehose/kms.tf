resource "aws_kms_key" "firehose_key" {
  description             = "KMS key for Kinesis Firehose encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}


resource "aws_kms_alias" "firehose_key_alias" {
  name          = "alias/kinesis-firehose-${var.environment}"
  target_key_id = aws_kms_key.firehose_key.key_id
}

