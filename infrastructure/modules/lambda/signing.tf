resource "aws_signer_signing_profile" "lambda_signing" {
  name_prefix = "eligibility-signing-"

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

output "lambda_signing_profile_name" {
  value = aws_signer_signing_profile.lambda_signing.name
}
