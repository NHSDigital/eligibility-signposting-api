# Deployment & Release Process

This repo uses GitHub Actions to deploy through four environments:

- **Dev** – continuous integration deploys on push to `main`. Creates a `Dev-<timestamp>` tag.
- **test** – Auto deploys the same commit that just deployed to Dev (but waits for approval). No releases or SemVer tags.
- **Preprod** – Auto deploys the commit that just deployed to test (but waits for approval)  **cuts/bumps a Release Candidate (RC)** tag (`vX.Y.Z-rc.N`) and creates a **GitHub pre-release**.
- **prod** – manual promotion of a specific RC to a **final SemVer tag** (`vX.Y.Z`) and a **GitHub Release**.

Releases are immutable and auditable:

- **RC tags** live only in Preprod.
- **Final tags** (`vX.Y.Z`) live only in prod and point to the exact commit that shipped.

---

## Workflow Map

| Stage            | Workflow file                                                           | Trigger                               | What it does                                                     | Tags / Releases                             |
|------------------|-------------------------------------------------------------------------|---------------------------------------|------------------------------------------------------------------|---------------------------------------------|
| **Pull Request** | `.github/workflows/cicd-1-pull-request.yml`                             | `pull_request` (opened/sync/reopened) | Commit/Test/Build/Acceptance stages                              | No tags/releases                            |
| **Dev**          | `.github/workflows/cicd-2-publish.yml`                                  | `push` to `main`                      | Builds & deploys to Dev                                          | Creates and pushes `Dev-YYYYMMDDHHMMSS` tag |
| **Test**         | `.github/workflows/cicd-3-test.yml`                                     | Auto (`workflow_run`)                 | Deploys the commit from the run that triggered it                | No tags, no releases                        |
| **Preprod**      | `.github/workflows/cicd-4-Preprod-deploy.yml` → calls `base-deploy.yml` | Auto (`workflow_run`)                 | Deploys the same commit **creates/bumps an RC tag**; pre-release | `vX.Y.Z-rc.N` + GitHub **pre-release**      |
| **Prod**         | `.github/workflows/cicd-5-prod-deploy.yml` → calls `base-deploy.yml`    | Manual (`workflow_dispatch`)          | Promotes a specific RC to final                                  | `vX.Y.Z` + GitHub **Release**               |

> **Note:** The Preprod/prod entry workflows are thin wrappers around a **reusable** workflow (`base-deploy.yml`).

### Lambda Artifact management

1. `Dev deploy` → artifact is created and stored in GitHub actions.
2. `Test deploy` → downloads the artifact from GitHub actions, uploads it to `Test` S3 and deploys to lambda.
3. `Preprod deploy` → downloads the artifact from `Test` S3, uploads it to `Preprod` S3 and deploys to lambda.
4. `Prod deploy` → downloads the artifact from `Preprod` s3, uploads it to `Prod` S3 and deploys to lambda.

---

## Pull Request Workflow (CI)

**File:** `CI/CD pull request`
**Trigger:** PR events (not drafts)

- Runs stages: **commit → test → build → acceptance** via reusable stage files:
  - `stage-1-commit.yaml`
  - `stage-2-test.yaml`
  - `stage-3-build.yaml`
  - `stage-4-acceptance.yaml`
- Does not deploy or create tags/releases.

---

## Dev Deployment (continuous on main)

**File:** `CI/CD publish`
**Trigger:** push to `main`

- Builds & deploys to **Dev**.
- Creates a timestamped **Dev tag**: `Dev-YYYYMMDDHHMMSS`
- No SemVer, no GitHub Release.

- Can be manually deployed to flow a candidate though pipeline outside of merge

**Why:** fast feedback and a stable pointer (the Dev tag) you can later promote to **test** or use as the **Preprod ref**.

---

## Test Deployment

**File:** `CI/CD deploy to TEST`
**Trigger:** Auto (`workflow_run`)

### Inputs

- taken from previous workflow

### Behavior

- Waits for approval to continue
- Checks out the ref, builds, and deploys to **test**.
- **No new tags** created. **No GitHub Releases** created.

---

## Preprod (Release Candidates)

**Entry workflow:** `cicd-4-Preprod-deploy.yml` → calls `base-deploy.yml`
**Trigger:** Auto (`workflow_run`) / Manual (`workflow_dispatch`)

### Inputs

- If Auto then no inputs needed at this point
- Auto will determine the release type from the label given to the PR linked to the commit being promoted
- If no Label is given it defaults to release candidate
- If Manual:
- **`ref`**: branch/tag/SHA to deploy (`Dev-<timestamp>` tag).
- **`release_type`**: one of:
  - `patch` – start a new **patch** series → `vX.Y.(Z+1)-rc.1`
  - `minor` – start a new **minor** series → `vX.(Y+1).0-rc.1`
  - `major` – start a new **major** series → `v(X+1).0.0-rc.1`
  - `rc` – **keep the same base** version and cut the **next RC** (e.g. `-rc.1` → `-rc.2`)
- **`reason`**: A short description of why manual is being used

### Behavior

- Tags the **checked-out commit** as the next **RC** (`vX.Y.Z-rc.N`) and pushes it.
- Deploys to **Preprod**.
- Creates a **GitHub pre-release** for that RC.

### When to use which `release_type`

- We should not normally be manually deploying, the auto deploy should take care of it
- Manual deploy to break glass
- Use **`patch`/`minor`/`major`** when starting a **new base version** (first RC becomes `-rc.1`).
- Use **`rc`** when you need another candidate for the **same base** (`-rc.N+1`).

---

## Prod (Final Releases)

**Entry workflow:** `cicd-5-prod-deploy.yml` → calls `base-deploy.yml`
**Trigger:** manual (`workflow_dispatch`)

### Inputs

- **`ref`**: the **RC tag** to promote (e.g. `v1.4.0-rc.2`).

### Behavior

- Validates the RC tag exists.
- Creates the corresponding **final tag** (e.g. `v1.4.0`) at the **same commit**.
- Deploys to **prod**.
- Creates a **GitHub Release**.

---

## Decision Guide (what to pick, when)

| Situation                                      | Workflow             | Input: `ref`                | Input: `release_type` | Result                                       |
|------------------------------------------------|----------------------|-----------------------------|-----------------------|----------------------------------------------|
| Deploy automatically after merge to main       | **Dev** (auto)       | `main` (implicit)           | n/a                   | Deploys to Dev, creates `Dev-YYYYMMDDHHMMSS` |
| Deploy an existing build to test               | **Test** (auto)      | n/a                         | n/a                   | Deploys to test (no tags/releases)           |
| Preprod deploy                                 | **Preprod** (auto)   | n/a                         | n/a                   | tags according to pr label + pre-release     |
| Break Glass **new patch release** into Preprod | **Preprod** (manual) | branch/tag/SHA              | `patch`               | `vX.Y.(Z+1)-rc.1` + pre-release              |
| Break Glass **new minor release** into Preprod | **Preprod**          | branch/tag/SHA              | `minor`               | `vX.(Y+1).0-rc.1` + pre-release              |
| Break Glass **new major release** into Preprod | **Preprod**          | branch/tag/SHA              | `major`               | `v(X+1).0.0-rc.1` + pre-release              |
| Break Glass **another candidate**              | **Preprod**          | branch/tag/SHA (same train) | `rc`                  | `vX.Y.Z-rc.N+1` + pre-release                |
| Promote a **tested RC** to production          | **Prod** (manual)    | RC tag (e.g. `v1.4.0-rc.2`) | n/a                   | `v1.4.0` + GitHub Release                    |

---

## Versioning Rules

- **Dev tags**: `Dev-YYYYMMDDHHMMSS` (automation convenience; never promoted to prod directly).
- **RC tags**: `vX.Y.Z-rc.N` (Preprod only; immutable; one per candidate).
- **Final tags**: `vX.Y.Z` (prod only; immutable; exactly what shipped).

### Promotion path

- Choose a commit (often via a **Dev tag**) → cut RC(s) in **Preprod** → promote the selected RC to **prod**.

---

## Common Q&A

**Can I use a Dev tag as the Preprod `ref`?**
Yes. `ref` can be any branch/tag/SHA. Using a `Dev-<timestamp>` tag guarantees you deploy the **same commit** previously built on Dev.

**What does `rc` mean?**
**Release Candidate**: a build that could become the final version if it passes testing. Each new candidate for the same base version increments the suffix: `-rc.1`, `-rc.2`, …

**What if I already have `v1.4.0-rc.1` and I need another Preprod build for the same release?**
Run **Preprod Deploy** with `release_type=rc` to get `v1.4.0-rc.2`.

**What if I discover issues after Preprod?**
Fix, then cut a new RC (`-rc.N+1`). Only promote to prod when ready.

---

## Quick Examples

### New minor release

1. Dev (auto) → creates `Dev-20250818…`.
2. Preprod (manual) → `ref=Dev-20250818…`, `release_type=minor` → `v1.4.0-rc.1`.
3. Preprod (manual) → `release_type=rc` → `v1.4.0-rc.2`.
4. Prod (manual) → `ref=v1.4.0-rc.2` → final `v1.4.0`.

### Same release, more candidates

- Already at `v1.3.3-rc.1`.
- Preprod → `release_type=rc` → `v1.3.3-rc.2`, test, repeat as needed.
- Prod → promote the stable RC to `v1.3.3`.
