import os
import sys

import pytest
from behave import scenarios

# Add the features directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# Import the step definitions
from features.steps.eligibility_check_steps import *

# Mark all tests as BDD tests
pytestmark = [pytest.mark.bdd, pytest.mark.eligibility]

# Load the scenarios from the feature file
scenarios("../../features/eligibility_check/eligibility_check.feature")
