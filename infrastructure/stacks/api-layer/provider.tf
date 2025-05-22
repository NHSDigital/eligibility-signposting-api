provider "aws" {
  region = "eu-west-2"
}

# Used by ACM
provider "aws" {
  alias  = "eu-west-2"
  region = "eu-west-2"
}
