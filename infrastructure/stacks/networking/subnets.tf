# Private Subnets
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_1_cidr
  availability_zone = local.availability_zone_1
  tags = {
    Name  = "private-subnet-1",
    Stack = local.stack_name
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_2_cidr
  availability_zone = local.availability_zone_2
  tags = {
    Name  = "private-subnet-2",
    Stack = local.stack_name
  }
}

resource "aws_subnet" "private_3" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_3_cidr
  availability_zone = local.availability_zone_3
  tags = {
    Name  = "private-subnet-3",
    Stack = local.stack_name
  }
}
