Feature: Full mTLS integration with real Eligibility API

  Background:
    Given AWS credentials are loaded from the environment
    And mTLS certificates are downloaded and available in the out/ directory

  Scenario Outline: Eligibility check returns 2xx response for NHS number queries
    Given I generate the test data files
    And I upload the test data files to DynamoDB
    Given I have the NHS number "<nhs_number>"
    When I query the eligibility API using the headers:

    Then the response status code should be 200
    And the response should be matching the JSON "<json_response>"
    Then I clean up DynamoDB test data

    Examples:
      | nhs_number | json_response |
      | 5000000001 | AUTO_RSV_SB_001.json |
      | 5000000002 | AUTO_RSV_SB_002.json |
      | 5000000003 | AUTO_RSV_SB_003.json |
      | 5000000004 | AUTO_RSV_SB_004.json |
      | 5000000005 | AUTO_RSV_SB_005.json |
      | 5000000006 | AUTO_RSV_SB_006.json |
      | 5000000007 | AUTO_RSV_SB_007.json |
      | 5000000008 | AUTO_RSV_SB_008.json |
      | 5000000009 | AUTO_RSV_SB_009.json |
      | 5000000010 | AUTO_RSV_SB_010.json |
      | 5000000011 | AUTO_RSV_SB_011.json |
      | 5000000012 | AUTO_RSV_SB_012.json |
      | 5000000013 | AUTO_RSV_SB_013.json |
      | 5000000014 | AUTO_RSV_SB_014.json |
