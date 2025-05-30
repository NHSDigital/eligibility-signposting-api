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
