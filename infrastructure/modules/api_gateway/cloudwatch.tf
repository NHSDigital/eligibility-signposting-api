resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.workspace}-${var.api_gateway_name}"
  retention_in_days = 365
  tags              = var.tags
  kms_key_id        = aws_kms_key.api_gateway.arn

  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_cloudwatch_log_data_protection_policy" "api_gateway_data_protection" {
  log_group_name = aws_cloudwatch_log_group.api_gateway.name
  policy_document = jsonencode({
    Name    = "data-protection-policy"
    Version = "2021-06-01"
    Statement = [
      {
        Sid      = "MaskSensitiveData"
        Effect   = "Deny"
        Principal = { "AWS" : "*" }
        Action   = "cloudwatch:PutLogEvents"
        Resource = "*"
        DataIdentifier = [
          "arn:aws:dataprotection::aws:data-identifier/DateOfBirth",
          "arn:aws:dataprotection::aws:data-identifier/UkPostcode",
          "arn:aws:dataprotection::aws:data-identifier/Custom:UkPostcodeSector",
          "arn:aws:dataprotection::aws:data-identifier/Custom:GpPracticeCode",
          "arn:aws:dataprotection::aws:data-identifier/Custom:13QFlag",
          "arn:aws:dataprotection::aws:data-identifier/Custom:CareHomeFlag",
          "arn:aws:dataprotection::aws:data-identifier/Custom:DEFlag",
          "arn:aws:dataprotection::aws:data-identifier/Custom:RemovalReasonCode",
          "arn:aws:dataprotection::aws:data-identifier/Custom:ValidDosesCount",
          "arn:aws:dataprotection::aws:data-identifier/Custom:InvalidDosesCount",
          "arn:aws:dataprotection::aws:data-identifier/Custom:LastSuccessfulDate",
          "arn:aws:dataprotection::aws:data-identifier/Custom:LastValidDoseDate",
          "arn:aws:dataprotection::aws:data-identifier/Custom:CohortLabel"

        ]
        Operation = {
          "cloudwatch:Mask" = {}
        }
      },
    ]
    CustomDataIdentifier = [
      {
        Name     = "UkPostcodeSector"
        Regex    = "[A-Z]{1,2}[0-9R-9][0A-Z]? ?[0-9]"
        Severity = "High"
      },
      {
        Name     = "GpPracticeCode"
        Regex    = "GP_PRACTICE[\\s\\\"':=]*([A-Z][0-9]{5})"
        Severity = "High"
      },
      {
        Name     = "13QFlag"
        Regex    = "13Q_FLAG[\\s\\\"':=]*[YN]"
        Severity = "High"
      },
      {
        Name     = "CareHomeFlag"
        Regex    = "CARE_HOME_FLAG[\\s\\\"':=]*[YN]"
        Severity = "High"
      },
      {
        Name     = "DEFlag"
        Regex    = "DE_FLAG[\\s\\\"':=]*[YN]"
        Severity = "High"
      },
      {
        Name     = "RemovalReasonCode"
        Regex    = "REMOVAL_REASON_CODE[\\s\\\"':=]*([A-Z]{3})"
        Severity = "High"
      },
      {
        Name     = "ValidDosesCount"
        Regex    = "VALID_DOSES_COUNT[\\s\\\"':=]*([0-9]{1,2}|100)"
        Severity = "High"
      },
      {
        Name     = "InvalidDosesCount"
        Regex    = "INVALID_DOSES_COUNT[\\s\\\"':=]*([0-9]{1,2}|100)"
        Severity = "High"
      },
      {
        Name     = "LastSuccessfulDate"
        Regex    = "LAST_SUCCESSFUL_DATE[\\s\\\"':=]*([0-9]{8})"
        Severity = "High"
      },
      {
        Name     = "LastValidDoseDate"
        Regex    = "LAST_VALID_DOSE_DATE[\\s\\\"':=]*([0-9]{8})"
        Severity = "High"
      },
      {
        Name     = "CohortLabel"
        Regex    = "COHORT_LABEL[\\s\\\"':=]*([A-Za-z0-9_ -]{1,100})"
        Severity = "High"
      }
    ]
  })
}
