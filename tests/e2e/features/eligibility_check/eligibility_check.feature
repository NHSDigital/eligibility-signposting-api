
Feature: Eligibility Check API
  As a consumer of the Eligibility Check API
  I want to verify the endpoint's response for various NHS numbers and parameters
  So that I can ensure the API behaves as expected for all supported scenarios

  Background:
    Given the Eligibility Check API base URL is configured

  Scenario Outline: Successful eligibility check returns 2xx and valid response
    Given I have the NHS number "<nhs_number>"
    When I request an eligibility check for the NHS number
    Then the response status code should be 2xx
    And the response content type should be application/json
    And the response should have a JSON body
    And the response should match the eligibility check schema

    Examples:
      | nhs_number    |
      | 50000000001   |
      | 50000000004   |
      | 9876543210    |

  Scenario Outline: Eligibility check with invalid or missing NHS number returns error
    Given I have the NHS number "<nhs_number>"
    When I request an eligibility check for the NHS number
    Then the response status code should be 4xx or 404

    Examples:
      | nhs_number    |
      | 00000000000   |
      |              |
      | patient=ABC  |

  Scenario Outline: Eligibility check with custom Accept header
    Given I have the NHS number "<nhs_number>"
    And I set the Accept header to "<accept_header>"
    When I request an eligibility check for the NHS number
    Then the response content type should contain "<expected_content_type>"

    Examples:
      | nhs_number    | accept_header           | expected_content_type    |
      | 9876543210    | application/json        | application/json        |
      | 9876543210    | application/json        | application/json   |

