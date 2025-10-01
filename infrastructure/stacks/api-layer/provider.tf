provider "aws" {
  region = "eu-west-2"

  default_tags {
    tags = local.tags
  }
}

# Used by ACM
provider "aws" {
  alias  = "eu-west-2"
  region = "eu-west-2"

  default_tags {
    tags = local.tags
  }
}
