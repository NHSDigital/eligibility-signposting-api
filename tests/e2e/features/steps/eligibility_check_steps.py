from behave import given, when, then
import requests
import jsonschema
from utils.config import BASE_URL, ELIGIBILITY_CHECK_SCHEMA, API_KEY

@given('the Eligibility Check API base URL is configured')
def step_impl_base_url(context):
    context.base_url = BASE_URL
    context.headers = {'apikey': API_KEY}


@given('I have the NHS number "{nhs_number}"')
def step_impl_nhs_number(context, nhs_number):
    context.nhs_number = nhs_number

@given('I have the NHS number ""')
def step_impl_empty_nhs_number(context):
    context.nhs_number = ""

@given('I set the Accept header to "{accept_header}"')
def step_impl_accept_header(context, accept_header):
    context.headers['Accept'] = accept_header

@when('I request an eligibility check for the NHS number')
def step_impl_request_eligibility_check(context):
    # Use the correct endpoint: /patient-check/{nhs_number}
    if context.nhs_number:
        url = f"{context.base_url}/patient-check/{context.nhs_number}"
    else:
        url = f"{context.base_url}/patient-check/"
    context.response = requests.get(url, headers=context.headers)

@then('the response status code should be 2xx')
def step_impl_status_code_2xx(context):
    assert 200 <= context.response.status_code < 300, f"Expected 2xx, got {context.response.status_code}"

@then('the response status code should be 4xx or 404')
def step_impl_status_code_4xx_or_404(context):
    assert (400 <= context.response.status_code < 500) or context.response.status_code == 404, \
        f"Expected 4xx or 404, got {context.response.status_code}"

@then('the response content type should be application/json')
def step_impl_content_type_json(context):
    assert "application/json" in context.response.headers.get("Content-Type", ""), \
        f"Content-Type is not application/json, got {context.response.headers.get('Content-Type', '')}"

@then('the response should have a JSON body')
def step_impl_has_json_body(context):
    try:
        context.response.json()
    except Exception:
        assert False, "Response does not have a JSON body"

@then('the response should match the eligibility check schema')
def step_impl_schema(context):
    jsonschema.validate(instance=context.response.json(), schema=ELIGIBILITY_CHECK_SCHEMA)

@then('the response content type should contain "{expected_content_type}"')
def step_impl_content_type_contains(context, expected_content_type):
    assert expected_content_type in context.response.headers.get("Content-Type", ""), \
        f"Content-Type does not contain {expected_content_type}, got {context.response.headers.get('Content-Type', '')}"

