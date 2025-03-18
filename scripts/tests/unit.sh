#!/bin/bash

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# This file is for you! Edit it to call your unit test suite. Note that the same
# file will be called if you run it locally as if you run it on CI.

# Replace the following line with something like:
#
#   rails test:unit
#   python manage.py test
#   npm run test
#
# or whatever is appropriate to your project. You should *only* run your fast
# tests from here. If you want to run other test suites, see the predefined
# tasks in scripts/test.mk.
UPSTREAM_HOST=test
make dependencies install-python
UPSTREAM_HOST=$UPSTREAM_HOST poetry run pytest tests/unit/ --durations=10 --cov-report= --cov src/eligibility_signposting_api/
poetry run python -m coverage xml
