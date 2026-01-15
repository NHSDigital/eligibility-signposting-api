# This file is for you! Edit it to implement your own hooks (make targets) into
# the project as automated steps to be executed on locally and in the CD pipeline
# ==============================================================================
include scripts/init.mk

MAKE_DIR := $(abspath $(shell pwd))
IMAGE_NAME := eligibility-signposting-api
# In CD, VERSION can be passed as an argument (e.g., make build VERSION=v1)
VERSION ?= latest

#Installs dependencies using poetry.
install-python:
	poetry install

#Configures Git Hooks, which are scripts that run given a specified event.
.git/hooks/pre-commit:
	cp scripts/pre-commit .git/hooks/pre-commit

#Condensed Target to run all targets above.
install: install-python .git/hooks/pre-commit

#Run the linting script (specified in package.json). Used to check the syntax and formatting of files.
lint:
	poetry run ruff format . --check
	poetry run ruff check .
	poetry run pyright

format: ## Format and fix code
	poetry run ruff format .
	poetry run ruff check . --fix-only

format_lint: format lint

#Files to loop over in release
_dist_include="pytest.ini poetry.lock poetry.toml pyproject.toml Makefile build/. tests"

# Example CI/CD targets are: dependencies, build, publish, deploy, clean, etc.

dependencies: # Install dependencies needed to build and test the project @Pipeline
	@echo "Fargate spike: dependencies handled via Dockerfile"

check-licenses:
	scripts/check_python_licenses.sh

.PHONY: build
build: ## Build docker image for Fargate
	# Use parent context as Dockerfile is in parent branch
	docker build --load -t $(IMAGE_NAME):$(VERSION) -f Dockerfile .

deploy: # Deploy the project artefact to the target environment @Pipeline
	# TODO: Implement the artefact deployment step

config:: # Configure development environment (main) @Configuration
	# TODO: Use only 'make' targets that are specific to this project, e.g. you may not need to install Node.js
	make _install-dependencies

precommit: test-unit build test-integration lint ## Pre-commit tasks
	python -m this

# ==============================================================================

${VERBOSE}.SILENT: \
	build \
	clean \
	config \
	dependencies \
	deploy \
