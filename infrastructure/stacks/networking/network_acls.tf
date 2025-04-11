# Network ACL for Private Subnets
resource "aws_network_acl" "private" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = [
    aws_subnet.private_1.id,
    aws_subnet.private_2.id,
    aws_subnet.private_3.id
  ]

  # Allow all outbound traffic from private subnets
  egress {
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = -1
    from_port  = 0
    to_port    = 0
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

  # Allow responses to outbound requests (ephemeral ports)
  ingress {
    rule_no    = 200
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = "tcp"
    from_port  = 1024
    to_port    = 65535
  }

  tags = {
    Name  = "private-nacl",
    Stack = local.stack_name
  }
}

# Network ACL for Public Subnets
resource "aws_network_acl" "public" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = [
    aws_subnet.public_1.id,
    aws_subnet.public_2.id,
    aws_subnet.public_3.id
  ]

  # Allow all outbound traffic from public subnets
  egress {
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = -1
    from_port  = 0
    to_port    = 0
  }

  # Allow inbound HTTP
  ingress {
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = "tcp"
    from_port  = 80
    to_port    = 80
  }

  # Allow inbound HTTPS
  ingress {
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = "tcp"
    from_port  = 443
    to_port    = 443
  }

  # Allow responses to outbound requests (ephemeral ports)
  ingress {
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    protocol   = "tcp"
    from_port  = 1024
    to_port    = 65535
  }

  # Allow inbound VPC traffic
  ingress {
    rule_no    = 130
    action     = "allow"
    cidr_block = local.vpc_cidr_block
    protocol   = -1
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name  = "public-nacl",
    Stack = local.stack_name
  }
}
