#!/usr/bin/env bash

REPORT_FAILURES=0
REPORT_WARNINGS=0
REPORT_CURRENT_SECTION=""
REPORT_MD_FILE=""
REPORT_JSON_FILE=""
REPORT_START_TIME=""

_report_json_append() {
  local level="$1"
  local message="$2"
  local section="${3:-}"

  python3 - "$REPORT_JSON_FILE" "$level" "$message" "$section" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
level = sys.argv[2]
message = sys.argv[3]
section = sys.argv[4]

data = json.loads(path.read_text())
data["entries"].append(
    {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "section": section,
        "message": message,
    }
)

if level == "warn":
    data["summary"]["warnings"] += 1
elif level == "fail":
    data["summary"]["failures"] += 1

path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

report_init() {
  REPORT_START_TIME="$(date -Iseconds)"
  REPORT_MD_FILE="$REPORT_DIR/devenv-$(date +%Y%m%d-%H%M%S).md"
  REPORT_JSON_FILE="${REPORT_MD_FILE%.md}.json"

  cat > "$REPORT_MD_FILE" <<EOF
# Developer Environment Report

- Timestamp: \`$REPORT_START_TIME\`
- Mode: \`$MODE\`
- Repo: \`$REPO_ROOT\`
- User: \`$USER\`
- Docker strategy: \`$DOCKER_STRATEGY\`

## Requested versions
- asdf: \`$ASDF_VERSION\`
- python: \`$PYTHON_VERSION\`
- poetry: \`$POETRY_VERSION\`
- nodejs: \`$NODE_VERSION\`
- terraform: \`$TERRAFORM_VERSION\`
- pre-commit: \`$PRECOMMIT_VERSION\`
- vale: \`$VALE_VERSION\`
- act: \`$ACT_VERSION\`

## Requested actions
- project setup: \`$RUN_PROJECT_SETUP\`
- validation: \`$RUN_VALIDATION\`
- unit tests: \`$RUN_UNIT_TESTS\`
- build: \`$RUN_BUILD\`
- integration tests: \`$RUN_INTEGRATION_TESTS\`
EOF

  python3 - "$REPORT_JSON_FILE" \
    "$REPORT_START_TIME" \
    "$MODE" \
    "$REPO_ROOT" \
    "$USER" \
    "$DOCKER_STRATEGY" \
    "$ASDF_VERSION" \
    "$PYTHON_VERSION" \
    "$POETRY_VERSION" \
    "$NODE_VERSION" \
    "$TERRAFORM_VERSION" \
    "$PRECOMMIT_VERSION" \
    "$VALE_VERSION" \
    "$ACT_VERSION" \
    "$RUN_PROJECT_SETUP" \
    "$RUN_VALIDATION" \
    "$RUN_UNIT_TESTS" \
    "$RUN_BUILD" \
    "$RUN_INTEGRATION_TESTS" <<'PY'
import json
import sys
from pathlib import Path

(
    path,
    start_time,
    mode,
    repo_root,
    user,
    docker_strategy,
    asdf_version,
    python_version,
    poetry_version,
    node_version,
    terraform_version,
    precommit_version,
    vale_version,
    act_version,
    run_project_setup,
    run_validation,
    run_unit_tests,
    run_build,
    run_integration_tests,
) = sys.argv[1:]

data = {
    "metadata": {
        "startTime": start_time,
        "mode": mode,
        "repoRoot": repo_root,
        "user": user,
        "dockerStrategy": docker_strategy,
        "versions": {
            "asdf": asdf_version,
            "python": python_version,
            "poetry": poetry_version,
            "nodejs": node_version,
            "terraform": terraform_version,
            "pre-commit": precommit_version,
            "vale": vale_version,
            "act": act_version,
        },
        "actions": {
            "projectSetup": run_project_setup,
            "validation": run_validation,
            "unitTests": run_unit_tests,
            "build": run_build,
            "integrationTests": run_integration_tests,
        },
    },
    "entries": [],
    "summary": {
        "failures": 0,
        "warnings": 0,
        "result": "running",
    },
}
Path(path).write_text(json.dumps(data, indent=2) + "\n")
PY
}

report_section() {
  REPORT_CURRENT_SECTION="$1"
  printf '\n## %s\n' "$REPORT_CURRENT_SECTION" | tee -a "$REPORT_MD_FILE"
  _report_json_append "section" "$REPORT_CURRENT_SECTION" "$REPORT_CURRENT_SECTION"
}

report_info() {
  local message="$1"
  printf -- '- ℹ️ %s\n' "$message" | tee -a "$REPORT_MD_FILE"
  _report_json_append "info" "$message" "$REPORT_CURRENT_SECTION"
}

report_ok() {
  local message="$1"
  printf -- '- ✅ %s\n' "$message" | tee -a "$REPORT_MD_FILE"
  _report_json_append "ok" "$message" "$REPORT_CURRENT_SECTION"
}

report_warn() {
  local message="$1"
  REPORT_WARNINGS=$((REPORT_WARNINGS + 1))
  printf -- '- ⚠️ %s\n' "$message" | tee -a "$REPORT_MD_FILE"
  _report_json_append "warn" "$message" "$REPORT_CURRENT_SECTION"
}

report_fail() {
  local message="$1"
  REPORT_FAILURES=$((REPORT_FAILURES + 1))
  printf -- '- ❌ %s\n' "$message" | tee -a "$REPORT_MD_FILE"
  _report_json_append "fail" "$message" "$REPORT_CURRENT_SECTION"
}

report_finalize() {
  local result="$1"
  local end_time
  end_time="$(date -Iseconds)"

  cat >> "$REPORT_MD_FILE" <<EOF

## Summary
- Failures: \`$REPORT_FAILURES\`
- Warnings: \`$REPORT_WARNINGS\`
- Result: \`$result\`
- Finished: \`$end_time\`
EOF

  python3 - "$REPORT_JSON_FILE" "$REPORT_FAILURES" "$REPORT_WARNINGS" "$result" "$end_time" <<'PY'
import json
import sys
from pathlib import Path

path, failures, warnings, result, end_time = sys.argv[1:]
data = json.loads(Path(path).read_text())
data["summary"]["failures"] = int(failures)
data["summary"]["warnings"] = int(warnings)
data["summary"]["result"] = result
data["metadata"]["endTime"] = end_time
Path(path).write_text(json.dumps(data, indent=2) + "\n")
PY

  printf '\nReports written:\n- %s\n- %s\n' "$REPORT_MD_FILE" "$REPORT_JSON_FILE"
}