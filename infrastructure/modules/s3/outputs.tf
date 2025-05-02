output "storage_bucket_access_logs_arn" {
  value = aws_s3_bucket.storage_bucket_access_logs.arn
}

output "storage_bucket_access_logs_id" {
  value = aws_s3_bucket.storage_bucket_access_logs.id
}
