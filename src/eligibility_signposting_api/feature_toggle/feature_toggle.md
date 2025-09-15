# Feature Toggles

Feature toggles allow us to deploy code to production in a disabled state, enabling it later without a new deployment.

## How It Works

Our feature toggle system is built on **AWS Systems Manager (SSM) Parameter Store**.

1.  **Single Source of Truth**: AWS SSM is the single source of truth for the current state (`true` or `false`) of all feature toggles.
2.  **Infrastructure as Code**: Toggles are defined in Terraform, ensuring configuration is version-controlled and repeatable across environments.
3.  **CI/CD Validation**: The `required_toggles.txt` file in the repository lists all toggles the application requires. The CI/CD pipeline checks that every toggle in this file exists in AWS SSM before a deployment can proceed.
4.  **Runtime Caching**: The application code uses a cached `is_feature_enabled()` function to check a toggle's state at runtime, minimizing calls to AWS and ensuring high performance.

## Developer Workflow

### Step 1: Define the Toggle in feature_toggle.json

Adding a new toggle is a single-step process. You only need to add a new entry to the `feature_toggle.json` file. This file defines the toggle's metadata and its intended state for each environment.

`default_state`: The safe, production-like state (usually `false`).

`env_overrides`: An optional map to set a different state for specific environments (e.g., enabling the feature in `dev` and `test` for QA). If an environment is not listed, it uses the `default_state`.

**File: [feature_toggle.json](../../../scripts/feature_toggle/feature_toggle.json)**

```json
{
  "enable_dynamic_status_text": {
    "purpose": "Enables dynamic status text based on conditions.",
    "ticket": "ELI-427",
    "created": "2025-09-02",
    "default_state": false,
    "env_overrides": {
      "dev": true,
      "test": true
    }
  }
}
```

Our Terraform setup automatically reads this file and creates the corresponding SSM parameters. You do not need to write new Terraform code for each toggle.

**File: [ssm.tf](../../../infrastructure/stacks/api-layer/ssm.tf) (For Reference—No edits needed)**
```terraform
resource "aws_ssm_parameter" "feature_toggles" {
  for_each = jsondecode(file("${path.root}/scripts/feature_toggle/feature_toggle.json"))

  name  = "/${var.environment}/feature_toggles/${each.key}"
  type  = "String"

  value = lookup(each.value.env_overrides, var.environment, each.value.default_state)

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Purpose     = each.value.purpose
    Ticket      = each.value.ticket
    Created     = each.value.created
  }

  lifecycle {
    ignore_changes = [value]
  }
}
```

### Step 2: Implement the Toggle Logic

Import and use the `is_feature_enabled()` function to create a conditional code path.

**File (Example): `eligibility_signposting_api/services/calculators/eligibility_calculator.py`**

```python
from eligibility_signposting_api.feature_toggle.feature_toggle import is_feature_enabled

if is_feature_enabled("enable_dynamic_status_text"):
    # New feature logic
    status_text = self.get_status_text(active_iteration.status_text, ConditionName(cc.target), status)
else:
    # Existing (old) logic
    status_text = status.get_default_status_text(ConditionName(cc.target))
```

### Step 3: Test Both Scenarios

You must write unit tests that cover both the "on" and "off" states of the toggle. Use `pytest.mark.parametrize` to run the same test with both states and `unittest.mock.patch` to control the toggle's return value.

**Important**: The patch path must point to **where the function is used**, not where it is defined.

**File (Example): `tests/unit/services/calculators/test_eligibility_calculator.py`**

```python
import pytest
from unittest.mock import patch

@pytest.mark.parametrize(
    "enable_dynamic_status_text, expected_rsv_text",
    [
        (True, "You are not eligible to take RSV vaccine"), # Case 1: Toggle is ON
        (False, "We do not believe you can have it"),      # Case 2: Toggle is OFF
    ],
)
@patch("eligibility_signposting_api.services.calculators.eligibility_calculator.is_feature_enabled")
def test_status_text_is_conditional_on_toggle(
        mock_is_feature_enabled,
        enable_dynamic_status_text,
        expected_rsv_text,
        faker: Faker
):

    # This mock controls the toggle for the test run
    mock_is_feature_enabled.return_value = enable_dynamic_status_text

    # Given, When, Then...
    assert actual_text_from_audit == expected_rsv_text
```

### Step 4: Cleanup Process

Feature toggles are **technical debt**. Once a feature is fully released and stable, the toggle and all associated conditional logic must be removed.

Follow the **"Two-Ticket" Rule**:

1.  When you create a ticket to add a feature toggle, immediately create a second ticket to remove it.
2.  Link the two tickets.
3.  Once the feature is permanently enabled, schedule the cleanup ticket in an upcoming sprint to remove the toggle from:
    - The application code
    - All related test code
    - The `feature_toggle.json` file
