resource "aws_internet_gateway" "vpc_external_access" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "internet-gateway",
    Stack = local.stack_name
  }
}
