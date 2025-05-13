# Public Route Tables
resource "aws_route_table" "public_1" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name  = "public-route-1",
    Stack = local.stack_name
  }
}

resource "aws_route_table" "public_2" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name  = "public-route-2",
    Stack = local.stack_name
  }
}

resource "aws_route_table" "public_3" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name  = "public-route-3",
    Stack = local.stack_name
  }
}

# Associate Public Route Tables with Public Subnets
resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public_1.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public_2.id
}

resource "aws_route_table_association" "public_3" {
  subnet_id      = aws_subnet.public_3.id
  route_table_id = aws_route_table.public_3.id
}

# Private Route Tables
resource "aws_route_table" "private_1" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name  = "private-route-1",
    Stack = local.stack_name
  }
}

resource "aws_route_table" "private_2" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name  = "private-route-2",
    Stack = local.stack_name
  }
}

resource "aws_route_table" "private_3" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name  = "private-route-3",
    Stack = local.stack_name
  }
}

# Associate Private Route Tables with Private Subnets
resource "aws_route_table_association" "private_association_1" {
  subnet_id      = aws_subnet.private_1.id
  route_table_id = aws_route_table.private_1.id
}

resource "aws_route_table_association" "private_association_2" {
  subnet_id      = aws_subnet.private_2.id
  route_table_id = aws_route_table.private_2.id
}

resource "aws_route_table_association" "private_association_3" {
  subnet_id      = aws_subnet.private_3.id
  route_table_id = aws_route_table.private_3.id
}

# Egress Internet Access
resource "aws_route" "public_internet_access" {
  route_table_id         = aws_route_table.public_1.id
  destination_cidr_block = local.any_ip_cidr
  gateway_id             = aws_internet_gateway.vpc_external_access.id
}

resource "aws_route" "public_internet_access_2" {
  route_table_id         = aws_route_table.public_2.id
  destination_cidr_block = local.any_ip_cidr
  gateway_id             = aws_internet_gateway.vpc_external_access.id
}

resource "aws_route" "public_internet_access_3" {
  route_table_id         = aws_route_table.public_3.id
  destination_cidr_block = local.any_ip_cidr
  gateway_id             = aws_internet_gateway.vpc_external_access.id
}
