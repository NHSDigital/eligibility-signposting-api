output "ecr_repository_url" {
  value       = aws_ecr_repository.eligibility_api.repository_url
  description = "The URL of the ECR repository for pushing Docker images"
}
