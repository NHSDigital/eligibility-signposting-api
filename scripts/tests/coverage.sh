#!/bin/bash

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

make dependencies install-python
poetry run pytest tests/unit/ --durations=10 --cov-report= --cov src/eligibility_signposting_api
poetry run python -m coverage xml
