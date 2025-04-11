resource "aws_nat_gateway" "public_access_1" {
  allocation_id = aws_eip.nat_1.id
  subnet_id     = aws_subnet.public_1.id
  tags = {
    Name = "public-access-1",
    Stack = local.stack_name
  }
}

resource "aws_eip" "nat_1" {
  tags = {
    Name = "nat-elastic-ip-1",
    Stack = local.stack_name
  }
}

resource "aws_nat_gateway" "public_access_2" {
  allocation_id = aws_eip.nat_2.id
  subnet_id     = aws_subnet.public_2.id
  tags = {
    Name = "public-access-2",
    Stack = local.stack_name
  }
}

resource "aws_eip" "nat_2" {
  tags = {
    Name = "nat-elastic-ip-2",
    Stack = local.stack_name
  }
}

resource "aws_nat_gateway" "public_access_3" {
  allocation_id = aws_eip.nat_3.id
  subnet_id     = aws_subnet.public_3.id
  tags = {
    Name = "public-access-3",
    Stack = local.stack_name
  }
}

resource "aws_eip" "nat_3" {
  tags = {
    Name = "nat-elastic-ip-3",
    Stack = local.stack_name
  }
}
