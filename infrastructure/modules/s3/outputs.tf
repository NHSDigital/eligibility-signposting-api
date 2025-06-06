output "storage_bucket_access_logs_arn" {
  value = aws_s3_bucket.storage_bucket_access_logs.arn
}

output "storage_bucket_access_logs_id" {
  value = aws_s3_bucket.storage_bucket_access_logs.id
}

output "storage_bucket_arn" {
  value = aws_s3_bucket.storage_bucket.arn
}

output "storage_bucket_name" {
  value = aws_s3_bucket.storage_bucket.bucket
}

output "storage_bucket_id" {
  value = aws_s3_bucket.storage_bucket.id
}

output "storage_bucket_kms_key_arn" {
  value = aws_kms_key.storage_bucket_cmk.arn
}
