# Eligibility Signposting API Test Automation Framework

This repository contains a Python-based test automation framework for the Eligibility Signposting API. The framework uses pytest and requests to implement API tests that were previously executed manually using Postman. It also includes BDD-style tests using Behave (not pytest-bdd).

## Framework Structure

```
qa-automation/
├── tests/
│   └── eligibility_signposting/
│       ├── test_eligibility_check.py      # Tests for eligibility check endpoint
│       ├── test_eligibility_check_bdd.py  # BDD tests for eligibility check
│       └── conftest.py                    # Pytest fixtures
├── features/
│   ├── eligibility_check/
│   │   └── eligibility_check.feature      # Behave feature file
│   ├── steps/
│   │   └── eligibility_check_steps.py     # Behave step definitions
│   └── conftest.py                        # Behave fixtures (if needed)
├── utils/
│   ├── api_client.py                      # Reusable HTTP client
│   └── config.py                          # Environment config and schemas
├── .env                                   # Environment variables (not in version control)
├── pytest.ini                             # Pytest configuration
└── pyproject.toml                         # Poetry project file
```

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ivma1-nhs/qa-automation.git
   cd qa-automation
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```


3. Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   # Or see https://python-poetry.org/docs/#installation for details
   ```

4. Install dependencies:
   ```bash
   poetry install
   ```

4. Configure environment variables:
   - Copy the `.env.example` file to `.env` (if not already present)
   - Update the values in `.env` with your sandbox credentials

## Running Tests


### Running API (pytest) tests
Run all pytest-based tests:
```bash
poetry run pytest
```

Run a specific pytest test file:
```bash
poetry run pytest tests/eligibility_signposting/test_eligibility_check.py
```

### Running BDD tests with Behave
Run all Behave feature tests:
```bash
poetry run behave
```

This will discover and run all feature files in the `features/` directory using Behave.

## Extending the Framework

### Adding New Test Files

1. Create a new test file in the appropriate directory:
   ```python
   # tests/eligibility_signposting/test_new_feature.py
   import pytest
   
   @pytest.mark.new_feature
   class TestNewFeature:
       def test_something(self, api_client):
           # Test implementation
           pass
   ```

2. Add the new marker to pytest.ini if needed:
   ```ini
   markers =
       new_feature: marks tests related to the new feature
   ```


### Adding New BDD Tests (Behave)

1. Create a new feature file:
   ```gherkin
   # features/new_feature/new_feature.feature
   Feature: New Feature
     As a user of the Eligibility Signposting API
     I want to use the new feature
     So that I can achieve my goal

     Scenario: Successful use of new feature
       Given the API is available
       When I make a request to the new feature endpoint
       Then the response should be successful
   ```

2. Create step definitions:
   ```python
   # features/steps/new_feature_steps.py
   from behave import given, when, then

   @when('I make a request to the new feature endpoint')
   def step_impl_make_request(context):
       # Implementation
       pass

   @then('the response should be successful')
   def step_impl_check_success(context):
       # Implementation
       pass
   ```

3. Run the BDD tests with:
   ```bash
   poetry run behave
   ```

### Adding New API Endpoints

1. Update the config.py file with the new endpoint:
   ```python
   # utils/config.py
   NEW_ENDPOINT = '/new-endpoint'
   ```

2. Add a new method to the ApiClient class:
   ```python
   # utils/api_client.py
   def get_new_endpoint(self, param1, param2):
       url = f"{self.base_url}/new-endpoint"
       params = {"param1": param1, "param2": param2}
       response = requests.get(url, headers=self.headers, params=params)
       return response
   ```

### Adding New Response Schemas

1. Add the new schema to config.py:
   ```python
   # utils/config.py
   NEW_ENDPOINT_SCHEMA = {
       "type": "object",
       "properties": {
           # Schema definition
       }
   }
   ```

2. Use the schema in your tests:
   ```python
   from utils.config import NEW_ENDPOINT_SCHEMA
   import jsonschema
   
   def test_new_endpoint_schema(self, api_client):
       response = api_client.get_new_endpoint("value1", "value2")
       response_json = response.json()
       jsonschema.validate(instance=response_json, schema=NEW_ENDPOINT_SCHEMA)
   ```

### Adding DynamoDB Integration

When the DynamoDB-backed API is ready, you can extend the framework by:

1. Adding DynamoDB client configuration:
   ```python
   # utils/dynamo_client.py
   import boto3
   from utils.config import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY
   
   class DynamoClient:
       def __init__(self):
           self.client = boto3.client(
               'dynamodb',
               region_name=AWS_REGION,
               aws_access_key_id=AWS_ACCESS_KEY,
               aws_secret_access_key=AWS_SECRET_KEY
           )
       
       def get_item(self, table_name, key):
           response = self.client.get_item(
               TableName=table_name,
               Key=key
           )
           return response
   ```

2. Adding fixtures in conftest.py:
   ```python
   # tests/eligibility_signposting/conftest.py
   from utils.dynamo_client import DynamoClient
   
   @pytest.fixture
   def dynamo_client():
       return DynamoClient()
   ```

3. Using the DynamoDB client in tests:
   ```python
   def test_with_dynamodb(self, api_client, dynamo_client):
       # Test implementation using both API and DynamoDB
       pass
   ```

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on the state from other tests.
2. **Fixtures**: Use fixtures for common setup and teardown operations.
3. **Parameterization**: Use pytest's parameterize feature for testing multiple scenarios.
4. **Assertions**: Use descriptive assertions to make test failures clear.
5. **Documentation**: Document your tests with docstrings and comments.
6. **Environment Variables**: Use environment variables for sensitive information and configuration.

## Continuous Integration

This framework can be integrated with CI/CD pipelines:

1. Add a GitHub Actions workflow:
   ```yaml
   # .github/workflows/test.yml
   name: API Tests
   
   on:
     push:
       branches: [ main ]
     pull_request:
       branches: [ main ]
   
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
       - uses: actions/checkout@v2
       - name: Set up Python
         uses: actions/setup-python@v2
         with:
           python-version: '3.9'
       - name: Install dependencies
         run: |
           poetry install
       - name: Run tests
         run: |
           poetry run pytest --html=report.html
         env:
           BASE_URL: ${{ secrets.BASE_URL }}
           API_KEY: ${{ secrets.API_KEY }}
       - name: Upload test report
         uses: actions/upload-artifact@v2
         with:
           name: test-report
           path: report.html
   ```