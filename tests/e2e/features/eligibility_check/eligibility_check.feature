Feature: Full mTLS integration with real Eligibility API

  Background:
    Given AWS credentials are loaded from the environment
    And mTLS certificates are downloaded and available in the out/ directory

  Scenario Outline: Eligibility check returns 2xx response for NHS number queries
    Given I generate the test data files
    And I upload the test data files to DynamoDB
    Given I have the NHS number "<nhs_number>"
    When I query the eligibility API
    Then the response status code should be 200
    And the response should be matching the JSON "<json_response>"
    Then I clean up DynamoDB test data

    Examples:
      | nhs_number   | json_response        |
      | 5000000001   | AUTO_RSV_SB_001.json |
      | 5000000004   | AUTO_RSV_SB_004.json |
