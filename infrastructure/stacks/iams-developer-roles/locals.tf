locals {
  stack_name = "iams-developer-roles"
  lambda_signing_profile_name = "${terraform.workspace == "default" ? "" : "${terraform.workspace}"}EligibilityApiLambdaSigningProfile"
  lambda_signing_profile_arn  = "arn:aws:signer:${var.default_aws_region}:${data.aws_caller_identity.current.account_id}:/signing-profiles/${local.lambda_signing_profile_name}"
}
