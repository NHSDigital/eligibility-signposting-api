# Public Subnets
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnet_1_cidr
  availability_zone       = local.availability_zone_1
  map_public_ip_on_launch = false
  tags = {
    Name = "public-subnet-1",
    Stack = local.stack_name
  }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnet_2_cidr
  availability_zone       = local.availability_zone_2
  map_public_ip_on_launch = false
  tags = {
    Name = "public-subnet-2",
    Stack = local.stack_name
  }
}

resource "aws_subnet" "public_3" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnet_3_cidr
  availability_zone       = local.availability_zone_3
  map_public_ip_on_launch = false
  tags = {
    Name = "public-subnet-3",
    Stack = local.stack_name
  }
}

# Private Subnets
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_1_cidr
  availability_zone = local.availability_zone_1
  tags = {
    Name = "private-subnet-1",
    Stack = local.stack_name
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_2_cidr
  availability_zone = local.availability_zone_2
  tags = {
    Name = "private-subnet-2",
    Stack = local.stack_name
  }
}

resource "aws_subnet" "private_3" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_3_cidr
  availability_zone = local.availability_zone_3
  tags = {
    Name = "private-subnet-3",
    Stack = local.stack_name
  }
}
