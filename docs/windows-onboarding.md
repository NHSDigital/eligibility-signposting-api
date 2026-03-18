# Onboarding Guide — Windows + WSL2

A step-by-step guide to get the Eligibility Signposting API project running on a fresh Windows machine using WSL2. Each section includes the commands to run **and** verification checks so you can confirm things are working before moving on.

---

## Table of Contents

- [Onboarding Guide — Windows + WSL2](#onboarding-guide--windows--wsl2)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites (Before WSL + Onboarding)](#prerequisites-before-wsl--onboarding)
  - [0. Optional: Automated bootstrap from Windows (`devenv`)](#0-optional-automated-bootstrap-from-windows-devenv)
  - [1. Install WSL2](#1-install-wsl2)
    - [Verify](#verify)
  - [2. Initial WSL2 Setup](#2-initial-wsl2-setup)
    - [Verify](#verify-1)
  - [3. Install Core Build Tools](#3-install-core-build-tools)
  - [4. Install Docker Desktop](#4-install-docker-desktop)
    - [Docker Engine directly inside WSL2](#docker-engine-directly-inside-wsl2)
    - [Verify](#verify-2)
  - [5. Install asdf Version Manager](#5-install-asdf-version-manager)
    - [Verify](#verify-3)
  - [6. Install Python 3.13 via asdf](#6-install-python-313-via-asdf)
    - [Verify](#verify-4)
  - [7. Install Poetry](#7-install-poetry)
    - [Verify](#verify-5)
  - [8. Install Node.js via asdf](#8-install-nodejs-via-asdf)
    - [Verify](#verify-6)
  - [9. Install Terraform via asdf](#9-install-terraform-via-asdf)
    - [Verify](#verify-7)
  - [10. Install Other asdf Plugins](#10-install-other-asdf-plugins)
    - [Verify](#verify-8)
  - [11. Clone the Repository](#11-clone-the-repository)
    - [Verify](#verify-9)
  - [12. Install Project Dependencies](#12-install-project-dependencies)
    - [Verify](#verify-10)
  - [13. Run the Tests](#13-run-the-tests)
    - [Unit tests only (fast, no Docker needed)](#unit-tests-only-fast-no-docker-needed)
    - [Linting and type checking](#linting-and-type-checking)
    - [Full pre-commit suite (unit tests + build + integration + lint)](#full-pre-commit-suite-unit-tests--build--integration--lint)
    - [Verify](#verify-11)
  - [14. Build the Lambda Artifact](#14-build-the-lambda-artifact)
    - [Verify](#verify-12)
  - [15. Run Integration Tests (Docker)](#15-run-integration-tests-docker)
    - [Verify](#verify-13)
  - [16. Make Helper Commands](#16-make-helper-commands)
  - [17. IDE Setup — VS Code](#17-ide-setup--vs-code)
    - [Recommended approach: VS Code + Remote WSL](#recommended-approach-vs-code--remote-wsl)
    - [Recommended extensions](#recommended-extensions)
    - [Configure the Python interpreter](#configure-the-python-interpreter)
    - [Verify](#verify-14)
  - [18. Troubleshooting](#18-troubleshooting)
    - [`make: *** No rule to make target ...` or old Make version](#make--no-rule-to-make-target--or-old-make-version)
    - [Python build fails during `asdf install python`](#python-build-fails-during-asdf-install-python)
    - [`docker: permission denied`](#docker-permission-denied)
    - [Poetry can't find Python 3.13](#poetry-cant-find-python-313)
    - [Slow file I/O / tests taking forever](#slow-file-io--tests-taking-forever)
    - [`poetry install` fails with "Failed to create process"](#poetry-install-fails-with-failed-to-create-process)
    - [Docker Compose containers not starting](#docker-compose-containers-not-starting)
    - [Conflicting localstack images](#conflicting-localstack-images)
    - [`pre-commit` hook failures](#pre-commit-hook-failures)
  - [Quick Start Checklist](#quick-start-checklist)

---

## Prerequisites (Before WSL + Onboarding)

Before you start WSL setup or project onboarding, make sure you already have:

- Python installed on Windows and available on PATH (`python --version`).
- PowerShell available on Windows (PowerShell 7+ recommended).
- GitHub access to this repository with authentication configured for clone/push (SSH key, PAT, or GitHub CLI).

Quick check from a PowerShell terminal:

```powershell
python --version
pwsh --version
git remote -v
```

If `pwsh` is not installed, use Windows PowerShell (`powershell.exe`) and continue.

---

## 0. Optional: Automated bootstrap from Windows (`devenv`)

If you want to bootstrap a full WSL developer environment from a Windows PowerShell session, use the `devenv` runner.

Open **PowerShell 7+** at the repository root and run:

```powershell
python .\devenv\run.py
```

Compatibility shim:

```powershell
.\devenv\run.ps1
```

Platform override examples (for future non-Windows bootstrap paths):

```powershell
python .\devenv\run.py --platform windows-wsl
python .\devenv\run.py --platform macos
python .\devenv\run.py --platform linux-native
```

For macOS/Linux shells, use the wrapper:

```bash
bash ./devenv/run.sh --platform macos
bash ./devenv/run.sh --platform linux-native
```

The script prompts for:

- Mode: `check` (validate only) or `create` (apply changes)
- WSL username
- WSL password (single entry, no confirm prompt; validated immediately with up to 3 retries)
- GitHub username + Personal Access Token (PAT) in `create` mode when using HTTPS git remotes (used for clone/fetch/push without interactive username/password prompts)

PAT note: the token must have repository read/write permissions for this repo (for example classic `repo` scope, or equivalent fine-grained repository permissions).
Auth mode note: `create` uses non-interactive HTTPS auth headers for git operations, not terminal username/password prompts.
Base branch note: `create` checks out `git.default_base_branch` from `devenv/config/devenv.bootstrap.yaml`. That branch must exist on `origin` (or already exist locally in the WSL repo). If you point it at a feature branch, push that branch first.

In `check` mode, the bootstrap verifies the WSL user exists and validates credentials before continuing. It stops early if the user does not exist/cannot login or password validation fails.

What it does in `create` mode:

1. Verifies WSL and the `Ubuntu-24.04` distro are present.
2. Creates a WSL workspace at `/home/{user}/workspace`.
3. Clones the repo if missing, checks out `main`, creates an init branch, and optionally pushes it.
4. Runs the onboarding setup and validation steps (`make config`, `make install`, `make onboarding-check`, plus optional tests).

`create` uses a check-then-remediate pattern: if a prerequisite is missing or stale, it installs/updates it and continues (for example distro install, apt refresh + missing packages, git for first clone, Docker install/remediation, asdf tools, and project dependency setup).

During `create`, you will also see a live step summary banner (`[1/6]` to `[6/6]`) so you can track remediation progress in real time.

Use this when you want one guided entry point from Windows. Use the manual sections below when you want full control of each step.

---

## 1. Install WSL2

Open **PowerShell as Administrator** on Windows and run:

```powershell
wsl --install -d Ubuntu-24.04
```

This installs WSL2 with Ubuntu 24.04. You'll be prompted to create a Unix username and password — remember these, you'll need them for `sudo`.

Restart your machine if prompted, then open the **Ubuntu** app from the Start Menu.

### Verify

```bash
# Inside WSL2 (Ubuntu terminal):
wsl.exe --list --verbose
# You should see Ubuntu-24.04 with VERSION 2
cat /etc/os-release | grep VERSION
# Should show 24.04
```

> **Tip:** All remaining commands in this guide should be run inside your WSL2 Ubuntu terminal, **not** in PowerShell.

---

## 2. Initial WSL2 Setup

Update packages and install essential build tools:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  build-essential \
  curl \
  git \
  wget \
  unzip \
  zip \
  jq \
  libssl-dev \
  zlib1g-dev \
  libbz2-dev \
  libreadline-dev \
  libsqlite3-dev \
  libncursesw5-dev \
  xz-utils \
  tk-dev \
  libxml2-dev \
  libxmlsec1-dev \
  libffi-dev \
  liblzma-dev \
  ca-certificates \
  gnupg \
  lsb-release \
  software-properties-common
```

These libraries are needed to compile Python from source (which asdf does under the hood).

### Verify

```bash
gcc --version    # Should show gcc 13.x or later
make --version   # Should show GNU Make 4.x (well above the 3.82 minimum)
git --version    # Should show git 2.x
jq --version     # Should show jq-1.7 or later
```

---

## 3. Install Core Build Tools

GNU `sed` and GNU `grep` are already the defaults on Ubuntu in WSL2. Confirm:

```bash
sed --version | head -1   # GNU sed
grep --version | head -1  # GNU grep
```

No additional action needed — this section is only relevant for macOS users. On WSL2/Ubuntu you already have the GNU toolchain.

---

## 4. Install Docker Desktop

Docker is needed to run integration tests (localstack/moto) and to build the Lambda deployment artifact.

### Docker Engine directly inside WSL2

If you cannot use Docker Desktop (e.g. licensing), install Docker Engine inside WSL2:

```bash
# Add Docker's official GPG key and repo
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Allow your user to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker
```

### Verify

```bash
docker --version          # Should show Docker 27.x or later
docker compose version    # Should show Docker Compose v2.x
docker run hello-world    # Should print "Hello from Docker!"
```

If `docker run hello-world` fails with a permission error, log out and back in to pick up the group change, or run `newgrp docker`.

---

## 5. Install asdf Version Manager

The project uses [asdf](https://asdf-vm.com/) to pin tool versions (Python, Terraform, Node.js, Poetry, etc.) via the `.tool-versions` file.

```bash
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.16.7

# Add to your shell profile (bashrc for bash, or zshrc for zsh)
echo -e '\n# asdf version manager\n. "$HOME/.asdf/asdf.sh"\n. "$HOME/.asdf/completions/asdf.bash"' >> ~/.bashrc

# Reload shell
source ~/.bashrc
```

### Verify

```bash
asdf --version
# Should show 0.16.7 or similar
```

---

## 6. Install Python 3.13 via asdf

The project requires Python 3.13 (specified in `.tool-versions`).

```bash
asdf plugin add python
asdf install python 3.13.5
asdf global python 3.13.5
```

### Verify

```bash
python --version
# Must show: Python 3.13.5

which python
# Should point to ~/.asdf/shims/python
```

> **If the build fails**, you are probably missing C libraries. Re-run the `apt install` block from [step 2](#2-initial-wsl2-setup) and try again.

---

## 7. Install Poetry

The project uses [Poetry](https://python-poetry.org/) 2.x for dependency management.

```bash
asdf plugin add poetry
asdf install poetry 2.1.4
asdf global poetry 2.1.4
```

### Verify

```bash
poetry --version
# Must show: Poetry (version 2.1.4)
```

---

## 8. Install Node.js via asdf

Node.js is used by some tooling (Portman for Postman collection generation, pre-commit hooks, etc.).

```bash
asdf plugin add nodejs
asdf install nodejs 22.18.0
asdf global nodejs 22.18.0
```

### Verify

```bash
node --version
# Must show: v22.18.0

npm --version
# Should show 10.x
```

---

## 9. Install Terraform via asdf

Terraform is used for infrastructure provisioning.

```bash
asdf plugin add terraform
asdf install terraform 1.12.1
asdf global terraform 1.12.1
```

### Verify

```bash
terraform --version
# Must show: Terraform v1.12.1
```

---

## 10. Install Other asdf Plugins

The `.tool-versions` file also specifies `pre-commit`, `vale`, and `act`. Install them now:

```bash
asdf plugin add pre-commit
asdf install pre-commit 4.2.0

asdf plugin add vale
asdf install vale 3.11.2

asdf plugin add act
asdf install act 0.2.77
```

Or install everything from `.tool-versions` in one go (run this from the repo root after cloning):

```bash
# This installs every tool listed in .tool-versions
make config
```

### Verify

```bash
pre-commit --version   # 4.2.0
vale --version         # vale version 3.11.2
act --version          # act version 0.2.77
```

---

## 11. Clone the Repository

```bash
# Navigate to where you keep your projects
cd ~
git clone https://github.com/NHSDigital/eligibility-signposting-api.git
cd eligibility-signposting-api
```

> **Important:** Clone the repo **inside WSL2's filesystem** (e.g. `~/eligibility-signposting-api`), **not** on the Windows mount (`/mnt/c/...`). File I/O on `/mnt/c` is dramatically slower and causes issues with file watchers and Docker volume mounts.

### Verify

```bash
ls .tool-versions
# Should exist and show pinned versions

cat .tool-versions
# You should see python 3.13.5, poetry 2.1.4, terraform 1.12.1, etc.
```

---

## 12. Install Project Dependencies

From the repository root:

```bash
# Install all asdf-managed tools pinned in .tool-versions
make config

# Install Python dependencies via Poetry
make install
```

This will:

1. Install all asdf plugins and versions from `.tool-versions`.
2. Run `poetry install` to create a `.venv/` virtual environment and install all Python packages.
3. Set up the Git pre-commit hook.

### Verify

```bash
# Virtual environment exists
ls .venv/bin/python
# Should exist

# Poetry can find the venv
poetry env info
# Should show the .venv path and Python 3.13.5

# Key packages are installed
poetry run python -c "import flask; print(flask.__version__)"
# Should print 3.x

poetry run python -c "import pydantic; print(pydantic.__version__)"
# Should print 2.x
```

---

## 13. Run the Tests

### Unit tests only (fast, no Docker needed)

```bash
make test-unit
```

### Linting and type checking

```bash
make lint
```

### Full pre-commit suite (unit tests + build + integration + lint)

```bash
make precommit
```

### Verify

All commands should exit with code 0. If unit tests fail at this point, check:

- Your Python version is exactly 3.13.5 (`python --version`).
- `poetry install` completed without errors.
- You are in the repository root directory.

---

## 14. Build the Lambda Artifact

```bash
make build
```

This uses the `poetry-plugin-lambda-build` plugin to create `dist/lambda.zip` inside a Docker container matching the AWS Lambda runtime.

### Verify

```bash
ls -lh dist/lambda.zip
# Should exist and be several MB
```

> **Requires Docker** — the build runs inside a Docker container. Make sure Docker is running.

---

## 15. Run Integration Tests (Docker)

Integration tests use a [moto](https://github.com/getmotocode/moto) Docker container to mock AWS services (DynamoDB, S3, etc.).

```bash
make test-integration
```

This will:

1. Start the Docker Compose stack defined in `tests/docker-compose.mock_aws.yml`.
2. Run pytest against `tests/integration/`.
3. Tear down the containers.

### Verify

```bash
# Check Docker containers started correctly (in another terminal while tests run)
docker ps
# Should show moto-server and lambda-api containers
```

---

## 16. Make Helper Commands

The following `make` targets are available to help with onboarding:

| Command | Description |
|---|---|
| `make onboarding-check` | Verify all prerequisites are installed at the correct versions |
| `make onboarding-doctor` | Run a full health check: prerequisites, dependencies, Docker, and tests |
| `make install` | Install Python deps and Git hooks |
| `make config` | Install all asdf-managed tools from `.tool-versions` |
| `make dependencies` | Install Poetry and plugins (used by CI) |
| `make test-unit` | Run unit tests |
| `make test-integration` | Run integration tests (requires Docker) |
| `make lint` | Run ruff format check, ruff lint, pyright |
| `make format` | Auto-format code with ruff |
| `make build` | Build the Lambda deployment artifact |
| `make precommit` | Full pre-commit suite (test + build + integration + lint) |

Run `make onboarding-check` after completing setup to confirm everything is in order.

---

## 17. IDE Setup — VS Code

### Recommended approach: VS Code + Remote WSL

1. Install [VS Code](https://code.visualstudio.com/) on **Windows**.
2. Install the **WSL** extension (`ms-vscode-remote.remote-wsl`).
3. Open your WSL2 terminal, navigate to the repo, and run:

   ```bash
   code .
   ```

   This opens VS Code connected to WSL2, so all terminal commands, Python interpreters, and file access use the Linux filesystem.

### Recommended extensions

Install these from the VS Code Extensions panel:

- **Python** (`ms-python.python`) — IntelliSense, debugging, virtualenv detection
- **Pylance** (`ms-python.vscode-pylance`) — type checking (matches pyright used in CI)
- **Ruff** (`charliermarsh.ruff`) — linting and formatting
- **WSL** (`ms-vscode-remote.remote-wsl`) — remote development in WSL2
- **Docker** (`ms-azuretools.vscode-docker`) — Docker compose management
- **HashiCorp Terraform** (`hashicorp.terraform`) — Terraform syntax and validation
- **GitLens** (`eamodio.gitlens`) — Git blame and history

### Configure the Python interpreter

1. Open the Command Palette (`Ctrl+Shift+P`).
2. Type **Python: Select Interpreter**.
3. Choose the `.venv` interpreter at `./.venv/bin/python`.

### Verify

- Open any `.py` file in `src/` — you should see no red squiggly lines if pyright is configured correctly.
- Open the integrated terminal (`Ctrl+``) — it should be a WSL2 bash session, not PowerShell.

---

## 18. Troubleshooting

### `make: *** No rule to make target ...` or old Make version

WSL2 Ubuntu ships with GNU Make 4.x which is fine. If you somehow have an older version:

```bash
sudo apt install --reinstall make
make --version
```

### Python build fails during `asdf install python`

Missing C libraries. Run:

```bash
sudo apt install -y \
  libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
  libffi-dev liblzma-dev
asdf install python 3.13.5
```

### `docker: permission denied`

Your user isn't in the `docker` group:

```bash
sudo usermod -aG docker $USER
# Then log out and back in, or:
newgrp docker
```

### Poetry can't find Python 3.13

```bash
# Check asdf is resolving Python
which python
# Should be ~/.asdf/shims/python

python --version
# Must be 3.13.5

# Re-link Poetry to the correct Python
poetry env use $(which python)
poetry install
```

### Slow file I/O / tests taking forever

You likely cloned the repo onto the Windows filesystem (`/mnt/c/...`). Move it to the WSL2 native filesystem:

```bash
mv /mnt/c/Users/YourName/eligibility-signposting-api ~/
cd ~/eligibility-signposting-api
```

### `poetry install` fails with "Failed to create process"

The Poetry shim may be stale. Re-install:

```bash
asdf reshim poetry
poetry install
```

### Docker Compose containers not starting

```bash
# Check Docker is running
docker info

# If using Docker Desktop, ensure WSL integration is enabled for your distro
# Docker Desktop → Settings → Resources → WSL Integration → Enable Ubuntu-24.04

# Clean up and retry
docker compose -f tests/docker-compose.mock_aws.yml down -v
make test-integration
```

### Conflicting localstack images

If you've previously worked on other projects using older localstack:

```bash
docker rmi localstack/localstack
docker rmi motoserver/moto
make test-integration
```

### `pre-commit` hook failures

```bash
# Re-install hooks
pre-commit install --config scripts/config/pre-commit.yaml --install-hooks

# Run manually to see what's failing
pre-commit run --config scripts/config/pre-commit.yaml --all-files
```

---

## Quick Start Checklist

Use this as a rundown once you've been through the guide, or if you're setting up a second machine:

```bash
# 1. Inside WSL2 Ubuntu
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl git wget unzip jq libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev libncursesw5-dev xz-utils tk-dev \
  libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# 2. Install asdf
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.16.7
echo -e '\n. "$HOME/.asdf/asdf.sh"\n. "$HOME/.asdf/completions/asdf.bash"' >> ~/.bashrc
source ~/.bashrc

# 3. Clone and install
git clone https://github.com/NHSDigital/eligibility-signposting-api.git
cd eligibility-signposting-api
make config
make install

# 4. Verify
make onboarding-check
make test-unit
```
