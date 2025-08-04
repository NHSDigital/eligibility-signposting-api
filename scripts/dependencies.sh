#!/bin/bash

set -euo pipefail

# Use the python from PATH (set by setup-python)
PYTHON_BIN="${PYTHON_BIN:-python}"

if ! [ -x "$(command -v poetry)" ]; then
  if ! [ -x "$(command -v pipx)" ]; then
    $PYTHON_BIN -m pip install --user pipx --isolated
    $PYTHON_BIN -m pipx ensurepath
  fi
  pipx install poetry --python $PYTHON_BIN
fi

# Ensure poetry uses the correct python environment
poetry env use $PYTHON_BIN

poetry self add poetry-plugin-lambda-build@2.1.0 poetry-plugin-export@1.9.0
