# This file is for you! Edit it to implement your own hooks (make targets) into
# the project as automated steps to be executed on locally and in the CD pipeline.
# ==============================================================================
include scripts/init.mk

MAKE_DIR := $(abspath $(shell pwd))

#Installs dependencies using poetry.
install-python:
	poetry install

#Installs dependencies using npm.
install-node:
	npm install --legacy-peer-deps

#Configures Git Hooks, which are scripts that run given a specified event.
.git/hooks/pre-commit:
	cp scripts/pre-commit .git/hooks/pre-commit

#Condensed Target to run all targets above.
install: install-node install-python .git/hooks/pre-commit

#Run the npm linting script (specified in package.json). Used to check the syntax and formatting of files.
lint:
	# npm run lint
	poetry run ruff format . --check
	poetry run ruff check .
	poetry run pyright


format: ## Format and fix code
	poetry run ruff format .
	poetry run ruff check . --fix-only

#Creates the fully expanded OAS spec in json
publish: clean
	mkdir -p build
	mkdir -p sandbox/specification
	npm run publish 2> /dev/null
	cp build/eligibility-signposting-api.json sandbox/specification/eligibility-signposting-api.json
#Files to loop over in release
_dist_include="pytest.ini poetry.lock poetry.toml pyproject.toml Makefile build/. tests"

# Example CI/CD targets are: dependencies, build, publish, deploy, clean, etc.

dependencies: # Install dependencies needed to build and test the project @Pipeline
	scripts/dependencies.sh

.PHONY: build
build: dist/lambda.zip # Build lambda.zip in dist/

dist/lambda.zip: $(MAKE_DIR)/pyproject.toml $(MAKE_DIR)/poetry.lock $(shell find src -type f)
	poetry build-lambda -vv

deploy: # Deploy the project artefact to the target environment @Pipeline
	# TODO: Implement the artefact deployment step

config:: # Configure development environment (main) @Configuration
	# TODO: Use only 'make' targets that are specific to this project, e.g. you may not need to install Node.js
	make _install-dependencies

precommit: test-unit build test-integration lint ## Pre-commit tasks
	python -m this

SPEC_DIR := $(CURDIR)/specification
POSTMAN_DIR := $(SPEC_DIR)/postman

convert-postman: # Create Postman collection from OAS spec
	mkdir -p $(POSTMAN_DIR)
	cp $(SPEC_DIR)/eligibility-signposting-api.yaml $(POSTMAN_DIR)/
	docker build -t portman-converter -f $(POSTMAN_DIR)/Dockerfile $(SPEC_DIR)
	docker run --rm -v $(SPEC_DIR):/app portman-converter \
		portman -l /app/eligibility-signposting-api.yaml -o /app/postman/collection.json
	rm $(POSTMAN_DIR)/eligibility-signposting-api.yaml
# ==============================================================================

${VERBOSE}.SILENT: \
	build \
	clean \
	config \
	dependencies \
	deploy \
