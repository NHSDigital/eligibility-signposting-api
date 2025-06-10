import sys
from pathlib import Path

import pytest
from behave import scenarios

# Add the features directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Mark all tests as BDD tests
pytestmark = [pytest.mark.bdd, pytest.mark.eligibility]

# Load the scenarios from the feature file
scenarios("../../features/eligibility_check/eligibility_check.feature")
