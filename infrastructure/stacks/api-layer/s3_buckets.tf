module "s3_rules_bucket" {
  source       = "../../modules/s3"
  bucket_name  = "eli-rules-3"
  environment  = var.environment
  project_name = var.project_name
}

module "s3_audit_bucket" {
  source                 = "../../modules/s3"
  bucket_name            = "eli-audit-1"
  environment            = var.environment
  project_name           = var.project_name
  bucket_expiration_days = 180
}
