module "eligibility_status_table" {
  source             = "../../modules/dynamodb"
  workspace          = local.workspace
  table_name_suffix  = "eligibility_datastore"
  partition_key      = "NHS_NUMBER"
  partition_key_type = "S"
  sort_key           = "ATTRIBUTE_TYPE"
  sort_key_type      = "S"
  tags               = local.tags
  environment        = local.environment
  stack_name         = local.stack_name
}
