# Network ACL for Private Subnets
resource "aws_network_acl" "private" {
  vpc_id = aws_vpc.main.id
  subnet_ids = [
    aws_subnet.private_1.id,
    aws_subnet.private_2.id,
    aws_subnet.private_3.id
  ]

  # Allow outbound traffic from private subnets to VPC CIDR only
  egress {
    rule_no    = 100
    action     = "allow"
    cidr_block = local.vpc_cidr_block
    protocol   = -1
    from_port  = 0
    to_port    = 0
  }

  # Allow HTTPS egress for Gateway endpoints (S3 and DynamoDB)
  # Gateway endpoints use AWS prefix lists which can't be specified in NACLs
  # This allows HTTPS to any destination, but security groups still control actual access
  egress {
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = "tcp"
    from_port  = 443
    to_port    = 443
  }

  # Allow ephemeral port responses for Gateway endpoint traffic
  egress {
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = "tcp"
    from_port  = 1024
    to_port    = 65535
  }

  # Allow inbound traffic from within the VPC
  ingress {
    rule_no    = 100
    action     = "allow"
    cidr_block = local.vpc_cidr_block
    protocol   = -1
    from_port  = 0
    to_port    = 0
  }

  # Allow HTTPS responses from Gateway endpoints
  ingress {
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = "tcp"
    from_port  = 443
    to_port    = 443
  }

  # Block RDP access
  ingress {
    rule_no    = 150
    action     = "deny"
    cidr_block = "0.0.0.0/0"
    protocol   = "tcp"
    from_port  = 3389
    to_port    = 3389
  }

  # Allow responses to outbound requests (ephemeral ports) from VPC endpoints
  ingress {
    rule_no    = 200
    action     = "allow"
    cidr_block = local.vpc_cidr_block
    protocol   = "tcp"
    from_port  = 1024
    to_port    = 65535
  }

  tags = {
    Name  = "private-nacl",
    Stack = local.stack_name
  }
}
