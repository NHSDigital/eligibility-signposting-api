resource "aws_signer_signing_profile" "lambda_signing" {
  name = "${terraform.workspace == "default" ? "" : "${terraform.workspace}"}EligibilityApiLambdaSigningProfile"
  #aws signer is strict with names, does not like hyphens or underscores

  platform_id = "AWSLambda-SHA384-ECDSA"

  signature_validity_period {
    value = 365
    type  = "DAYS"
  }
}

resource "aws_lambda_code_signing_config" "signing_config" {
  allowed_publishers {
    signing_profile_version_arns = [
      aws_signer_signing_profile.lambda_signing.version_arn
    ]
  }

  policies {
    untrusted_artifact_on_deployment = "Enforce"
  }

  description = "Only allow Lambda bundles signed by our trusted signer profile"
}
