module "tfstate" {
  source = "../../modules/bootstrap/tfstate"

  project_name = var.project_name
  environment  = var.environment
}
