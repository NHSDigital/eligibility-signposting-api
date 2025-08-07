module "s3_rules_bucket" {
  source       = "../../modules/s3"
  bucket_name  = "eli-rules"
  environment  = var.environment
  project_name = var.project_name
  stack_name   = local.stack_name
  workspace    = terraform.workspace
}

module "s3_audit_bucket" {
  source                 = "../../modules/s3"
  bucket_name            = "eli-audit"
  environment            = var.environment
  project_name           = var.project_name
  bucket_expiration_days = 180
  stack_name             = local.stack_name
  workspace              = terraform.workspace
}
