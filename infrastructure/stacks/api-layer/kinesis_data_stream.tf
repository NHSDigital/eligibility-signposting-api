resource "aws_kms_key" "kinesis_data_stream_kms_key" {
  description             = "${terraform.workspace == "default" ? "" : "${terraform.workspace}-"} kinesis_data_stream_kms Master Key"
  deletion_window_in_days = 14
  is_enabled              = true
  enable_key_rotation     = true
}

resource "aws_kinesis_stream" "kinesis_source_stream" {
  name             = "${var.project_name}-${var.environment}-kinesis-audit-stream"
  retention_period = 24

  stream_mode_details {
    stream_mode = "ON_DEMAND" # can discuss later
  }

  encryption_type = "KMS"
  kms_key_id      = aws_kms_key.kinesis_data_stream_kms_key.arn
}
