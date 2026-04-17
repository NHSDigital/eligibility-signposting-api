locals {
  stack_name = "iams-developer-roles"
  dev_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-reserved/sso.amazonaws.com/${var.default_aws_region}/AWSReservedSSO_vdselid_${var.environment}_d92ae328ac8d84c7"
  lambda_signing_profile_name = "${terraform.workspace == "default" ? "" : "${terraform.workspace}"}EligibilityLambdaSigningProfile"
  lambda_signing_profile_arn  = "arn:aws:signer:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:/signing-profiles/${local.lambda_signing_profile_name}"
}
