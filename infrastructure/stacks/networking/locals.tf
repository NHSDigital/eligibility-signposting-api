locals {
  any_ip_cidr           = "0.0.0.0/0"
  vpc_cidr_block        = "10.0.0.0/16"
  private_subnet_1_cidr = "10.0.6.0/24"
  private_subnet_2_cidr = "10.0.7.0/24"
  private_subnet_3_cidr = "10.0.8.0/24"
  availability_zone_1   = "eu-west-2a"
  availability_zone_2   = "eu-west-2b"
  availability_zone_3   = "eu-west-2c"
  default_port          = 443

  region     = "eu-west-2"
  stack_name = "Networking"

  # VPC Interface Endpoints
  vpc_interface_endpoints = {
    kms               = "com.amazonaws.${local.region}.kms"
    cloudwatch-logs   = "com.amazonaws.${local.region}.logs"
    ssm               = "com.amazonaws.${local.region}.ssm"
    secrets-manager   = "com.amazonaws.${local.region}.secretsmanager"
    lambda            = "com.amazonaws.${local.region}.lambda"
    sts               = "com.amazonaws.${local.region}.sts"
    sqs               = "com.amazonaws.${local.region}.sqs"
    kinesis-firehose  = "com.amazonaws.${local.region}.kinesis-firehose"
  }

  # VPC Gateway Endpoints
  vpc_gateway_endpoints = {
    dynamodb = "com.amazonaws.${local.region}.dynamodb"
    s3       = "com.amazonaws.${local.region}.s3"
  }
}
