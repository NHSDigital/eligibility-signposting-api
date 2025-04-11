terraform {
  required_version = ">= 1.11.1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.6, != 5.71.0"
    }
  }
  backend "s3" {
    bucket = "eligibility-signposting-api-dev-tfstate"
    key    = "tfstate/networking.tfstate"
    region = "eu-west-2"
    use_lockfile = true
  }
}
