module "eligibility_status_table" {
  source             = "../../modules/dynamodb"
  workspace          = local.workspace
  table_name         = "eligibilty_datastore"
  partition_key      = "NHS_NUMBER"
  partition_key_type = "S"
  sort_key           = "ATTRIBUTE_TYPE"
  sort_key_type      = "S"
}
