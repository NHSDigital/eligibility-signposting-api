locals {
  # tflint-ignore: terraform_unused_declarations
  environment = var.environment
  # tflint-ignore: terraform_unused_declarations
  workspace = lower(terraform.workspace)
  # tflint-ignore: terraform_unused_declarations
  runtime = "python3.13.1"

  # tflint-ignore: terraform_unused_declarations
  tags = {
    # Billing and Identification (FinOps)
    FinOpsTagVersion = "1"
    Programme        = "Vaccinations"
    Product          = "EligibilitySignpostingAPI"
    Owner            = "edd.almond1@nhs.net" # REQUIRED - distribution list recommended
    CostCentre       = "129117"              # REQUIRED - your cost centre code
    Customer         = "NHS England"         # Optional but recommended

    # Environment Information (SecOps)
    data_classification = "5"             # REQUIRED - 1-5 based on Cloud Risk Model
    DataType            = "PII"           # REQUIRED - adjust based on your data
    Environment         = var.environment # REQUIRED - Development/Testing/Preproduction/Production
    ProjectType         = "Production"    # REQUIRED - PoC/Pilot/Production
    PublicFacing        = "Y"             # REQUIRED - Y/N for internet-facing

    # Technical Operations (TechOps)
    ServiceCategory = "Silver"   # REQUIRED - Bronze/Silver/Gold/Platinum
    OnOffPattern    = "AlwaysOn" # REQUIRED - AlwaysOn/OfficeHours/MF86/MF95/MF77

    # Application Information (DevOps)
    ApplicationRole = "API"       # REQUIRED - Web/App/DB/WebServer/Firewall/LoadBalancer
    Tool            = "Terraform" # Optional - None/Terraform/Packer/CloudFormation/ARM

    # Custom/Internal
    workspace = lower(terraform.workspace)
    Stack     = local.stack_name
  }

  terraform_state_bucket_name = "eligibility-signposting-api-${var.environment}-tfstate"
  terraform_state_bucket_arn  = "arn:aws:s3:::eligibility-signposting-api-${var.environment}-tfstate"

  role_arn_pre  = "arn:aws:iam::603871901111:role/db-system-worker"
  role_arn_prod = "arn:aws:iam::232116723729:role/db-system-worker"

  selected_role_arn = var.environment == "prod" ? local.role_arn_prod : local.role_arn_pre
}
