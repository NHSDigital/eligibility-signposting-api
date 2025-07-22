resource "aws_vpc" "main" {
  #checkov:skip=CKV2_AWS_11: "Ensure VPC flow logging is enabled in all VPCs"
  cidr_block           = local.vpc_cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name  = "main-vpc"
    Stack = local.stack_name
  }
}

# Default Deny All Security Group
resource "aws_default_security_group" "default_vpc" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    local.tags,
    {
      Name  = "main-vpc"
      Stack = local.stack_name
    }
  )
}

# EC2.172 - block internet gateway access at the account level
resource "aws_vpc_block_public_access_options" "default_vpc" {
  internet_gateway_block_mode = "block-bidirectional"
}
