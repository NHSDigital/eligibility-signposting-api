output "security_group_ids" {
  description = "security group id"
  value       = [aws_security_group.main.id]
}

output "vpc_intra_subnets" {
  description = "private subnet for resources"
  value       = [aws_subnet.private_1.id, aws_subnet.private_2.id, aws_subnet.private_3.id]
}
