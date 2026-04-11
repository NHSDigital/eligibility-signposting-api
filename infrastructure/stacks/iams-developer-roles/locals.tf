locals {
  stack_name = "iams-developer-roles"
  dev_role_arn = "arn:aws:iam::448049830832:role/aws-reserved/sso.amazonaws.com/eu-west-2/AWSReservedSSO_vdselid_dev_d92ae328ac8d84c7"
  lambda_signing_profile_name = "${terraform.workspace == "default" ? "" : "${terraform.workspace}"}EligibilityApiLambdaSigningProfile"
  lambda_signing_profile_arn  = "arn:aws:signer:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:/signing-profiles/${local.lambda_signing_profile_name}"
}
