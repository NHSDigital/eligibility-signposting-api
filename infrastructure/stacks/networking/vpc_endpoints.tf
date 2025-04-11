# Generate Security Group used by all VPC Endpoints:
resource "aws_security_group" "main" {
  name        = "main-security-group"
  description = "Allows all internal to VPC resources access to the endpoints and the endpoints to access the AWS Services"
  vpc_id      = aws_vpc.main.id
  tags = {
    "Name" = "main-security-group",
    Stack  = local.stack_name
  }
}

resource "aws_security_group_rule" "main_https_in" {
  description       = "Allow all internal VPC resources access to all VPC Endpoints"
  type              = "ingress"
  from_port         = local.default_port
  to_port           = local.default_port
  protocol          = "tcp"
  cidr_blocks       = [local.vpc_cidr_block]
  security_group_id = aws_security_group.main.id
}

resource "aws_security_group_rule" "main_https_out" {
  description       = "Allow VPC Endpoint to access the actual AWS Service Endpoints"
  type              = "egress"
  from_port         = local.default_port
  to_port           = local.default_port
  protocol          = "tcp"
  cidr_blocks       = [local.any_ip_cidr]
  security_group_id = aws_security_group.main.id
}

# Generate the Interface VPC Endpoints
resource "aws_vpc_endpoint" "interfaces" {
  vpc_id       = aws_vpc.main.id
  for_each     = local.vpc_interface_endpoints
  service_name = each.value
  subnet_ids = [
    aws_subnet.private_1.id,
    aws_subnet.private_2.id,
    aws_subnet.private_3.id
  ]
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.main.id]

  tags = {
    "Name" = "${each.key}-endpoint",
    Stack  = local.stack_name
  }
}

# Generate the Gateway VPC Endpoints
resource "aws_vpc_endpoint" "gateways" {
  vpc_id            = aws_vpc.main.id
  for_each          = local.vpc_gateway_endpoints
  service_name      = each.value
  vpc_endpoint_type = "Gateway"
  route_table_ids = [
    aws_route_table.private_1.id,
    aws_route_table.private_2.id,
    aws_route_table.private_3.id
  ]

  tags = {
    "Name" = "${each.key}-endpoint",
    Stack  = local.stack_name
  }
}
