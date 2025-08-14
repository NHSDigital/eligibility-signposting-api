# Blue-Green Deployment Outputs

output "blue_green_enabled" {
  description = "Whether blue-green deployment is enabled"
  value       = local.enable_blue_green
}

output "lambda_blue_alias_arn" {
  description = "ARN of the Lambda blue alias"
  value       = var.environment == "prod" ? aws_lambda_alias.blue[0].arn : null
}

output "lambda_green_alias_arn" {
  description = "ARN of the Lambda green alias"
  value       = var.environment == "prod" ? aws_lambda_alias.green[0].arn : null
}

output "lambda_production_alias_arn" {
  description = "ARN of the Lambda production alias with weighted routing"
  value       = var.environment == "prod" ? aws_lambda_alias.production[0].arn : null
}

output "current_traffic_distribution" {
  description = "Current traffic distribution between blue and green"
  value = var.environment == "prod" ? {
    blue_weight  = local.blue_weight
    green_weight = local.green_weight
  } : null
}

output "deployment_instructions" {
  description = "Quick reference for blue-green deployment commands"
  value = var.environment == "prod" ? {
    deploy_green    = "./scripts/blue-green-deploy.sh deploy-green"
    canary_deploy   = "./scripts/blue-green-deploy.sh canary <version>"
    promote_green   = "./scripts/blue-green-deploy.sh promote <version>"
    rollback        = "./scripts/blue-green-deploy.sh rollback"
    manual_shift    = "./scripts/blue-green-deploy.sh shift-traffic <blue_weight> <green_version>"
    health_check    = "make blue-green-health"
  } : "Blue-green deployment not enabled in non-production environments"
}
