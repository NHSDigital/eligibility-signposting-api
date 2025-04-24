module "eligibility_status_table" {
  source             = "../../modules/dynamodb"
  workspace          = local.workspace
  stack_name         = local.stack_name
  table_name         = "latest_registrations"
  partition_key      = "nhs_number"
  partition_key_type = "S"
}
