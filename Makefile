# This file is for you! Edit it to implement your own hooks (make targets) into
# the project as automated steps to be executed on locally and in the CD pipeline
# ==============================================================================
include scripts/init.mk

MAKE_DIR := $(abspath $(shell pwd))

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

vulture:
	poetry run vulture

#Files to loop over in release
_dist_include="pytest.ini poetry.lock poetry.toml pyproject.toml Makefile build/. tests"

# Example CI/CD targets are: dependencies, build, publish, deploy, clean, etc.

dependencies: # Install dependencies needed to build and test the project @Pipeline
	scripts/dependencies.sh

check-licenses:
	scripts/check_python_licenses.sh

.PHONY: build
build: dist/lambda.zip # Build lambda.zip in dist/

dist/lambda.zip: $(MAKE_DIR)/pyproject.toml $(MAKE_DIR)/poetry.lock $(shell find src -type f)
	poetry build-lambda -vv && poetry run clean-lambda

deploy: # Deploy the project artefact to the target environment @Pipeline
	# TODO: Implement the artefact deployment step

config:: # Configure development environment (main) @Configuration
	# TODO: Use only 'make' targets that are specific to this project, e.g. you may not need to install Node.js
	make _install-dependencies

precommit: test-unit build test-integration lint vulture ## Pre-commit tasks
	python -m this

# ==============================================================================
# Onboarding helpers

REQUIRED_PYTHON_VERSION := 3.13
REQUIRED_POETRY_VERSION := 2.1
REQUIRED_TERRAFORM_VERSION := 1.12
REQUIRED_NODE_VERSION := 22

.PHONY: onboarding-check
onboarding-check: ## Check all prerequisites are installed at expected versions
	@echo "=== Onboarding prerequisite check ==="
	@echo ""
	@printf "%-18s" "Python:" && \
		(python --version 2>/dev/null | grep -q "$(REQUIRED_PYTHON_VERSION)" \
		&& echo "OK ($$(python --version 2>&1))" \
		|| (echo "MISSING or wrong version (need $(REQUIRED_PYTHON_VERSION).x)" && false))
	@printf "%-18s" "Poetry:" && \
		(poetry --version 2>/dev/null | grep -q "$(REQUIRED_POETRY_VERSION)" \
		&& echo "OK ($$(poetry --version 2>&1))" \
		|| (echo "MISSING or wrong version (need $(REQUIRED_POETRY_VERSION).x)" && false))
	@printf "%-18s" "Node.js:" && \
		(node --version 2>/dev/null | grep -q "v$(REQUIRED_NODE_VERSION)" \
		&& echo "OK ($$(node --version 2>&1))" \
		|| (echo "MISSING or wrong version (need v$(REQUIRED_NODE_VERSION).x)" && false))
	@printf "%-18s" "Terraform:" && \
		(terraform --version 2>/dev/null | head -1 | grep -q "$(REQUIRED_TERRAFORM_VERSION)" \
		&& echo "OK ($$(terraform --version 2>/dev/null | head -1))" \
		|| (echo "MISSING or wrong version (need $(REQUIRED_TERRAFORM_VERSION).x)" && false))
	@printf "%-18s" "Docker:" && \
		(docker --version 2>/dev/null \
		&& true \
		|| (echo "MISSING — install Docker Desktop or Docker Engine" && false))
	@printf "%-18s" "Docker Compose:" && \
		(docker compose version 2>/dev/null \
		&& true \
		|| (echo "MISSING — install Docker Compose plugin" && false))
	@printf "%-18s" "GNU Make:" && \
		(make --version 2>/dev/null | head -1 | grep -q "GNU Make" \
		&& echo "OK ($$(make --version | head -1))" \
		|| (echo "MISSING or not GNU Make" && false))
	@printf "%-18s" "jq:" && \
		(jq --version 2>/dev/null \
		&& true \
		|| (echo "MISSING — apt install jq" && false))
	@printf "%-18s" "Git:" && \
		echo "OK ($$(git --version))"
	@printf "%-18s" "asdf:" && \
		(asdf --version 2>/dev/null \
		&& true \
		|| (echo "MISSING — see ONBOARDING.md" && false))
	@echo ""
	@echo "=== All prerequisite checks passed ==="

.PHONY: onboarding-doctor
onboarding-doctor: ## Full health check: prerequisites, deps, Docker, and unit tests
	@echo ">>> Step 1/4: Checking prerequisites..."
	make onboarding-check
	@echo ""
	@echo ">>> Step 2/4: Checking Python dependencies..."
	@(test -d .venv && poetry run python -c "import flask" 2>/dev/null \
		&& echo "OK — .venv exists and key packages importable" \
		|| (echo "FAIL — run 'make install' first" && false))
	@echo ""
	@echo ">>> Step 3/4: Checking Docker is responsive..."
	@(docker info > /dev/null 2>&1 \
		&& echo "OK — Docker daemon reachable" \
		|| (echo "FAIL — Docker is not running" && false))
	@echo ""
	@echo ">>> Step 4/4: Running unit tests..."
	UPSTREAM_HOST=test poetry run pytest tests/unit/ -x -q --tb=short 2>&1 | tail -5
	@echo ""
	@echo "=== Doctor complete — you are good to go! ==="

# ==============================================================================

${VERBOSE}.SILENT: \
	build \
	clean \
	config \
	dependencies \
	deploy \
