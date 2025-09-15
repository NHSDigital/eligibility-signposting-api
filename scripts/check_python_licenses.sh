#!/bin/bash
set -euo pipefail

# known packages with dual licensing
IGNORE_PACKAGES="PyGithub chardet text-unidecode pyzmq"
LICENSES=$(poetry run pip-licenses  --ignore-packages "${IGNORE_PACKAGES}")
INCOMPATIBLE_LIBS=$(echo "$LICENSES" | grep 'GPL' || true)

if [[ -z $INCOMPATIBLE_LIBS ]]; then
    echo "The libraries were checked and no license issues were found."
    exit 0
else
    echo "The following libraries were found which are not compatible with this project's license:"
    echo "$INCOMPATIBLE_LIBS"
    exit 1
fi
