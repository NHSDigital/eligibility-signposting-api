# Tableau DQ Metrics

This README describes the process
for publishing the DQ metrics data from AWS S3 to the Tableau Server.

There are two methods for publishing the data to Tableau Server:

1. [Running the Python scripts locally](#python-scripts)
2. Using the [GitHub Actions workflow](#github-actions-workflow) to run the scripts on a schedule

## Overview

This section provides an overview of the process for publishing DQ metrics data to Tableau Server.

The Python scripts are used to generate a Tableau `.hyper` datasource file from the DQ metric
JSON files stored in S3.
This `.hyper` file is then published to Tableau Server by overwriting an existing datasource.
Once this datasource is updated, a ping is sent to a Tableau view to trigger a cache refresh,
ensuring that the latest data is updated and available for visualisation.

The following sections provide more details on the Python scripts and the GitHub Actions workflow that automates this process.

## Python Scripts

There are two Python scripts involved:

- `generate_tableau_data.py`
  Reads DQ metric JSON files from the S3 bucket `eligibility-signposting-api-dev-dq-metrics`, filters to approximately the last 3 months, and writes a Tableau Hyper extract called `converted.hyper`.

- `tableau_refresh.py`
  Publishes `./converted.hyper` to Tableau Server by overwriting an existing datasource, then pings a Tableau view to trigger a cache refresh.

This work supports the EliD DQ metrics Tableau MVP, where Tableau is being used to visualise DQ metrics for monitoring and comparison against expected thresholds.

---

### What the scripts do

#### 1. Generate Hyper extract

`generate_tableau_data.py`:

- connects to S3
- scans daily `processing_date=YYYYMMDD/` prefixes for the last 90 days
- reads `.json` files from the bucket
- parses JSON or JSONL content into a pandas DataFrame
- creates a Tableau Hyper file named `converted.hyper`

The S3 source bucket is currently hard coded as:

```python
S3_BUCKET = "eligibility-signposting-api-dev-dq-metrics"
```

and the output file is:

```python
LOCAL_HYPER_PATH = "converted.hyper"
```

#### 2. Publish to Tableau

`tableau_refresh.py`:

- checks that `./converted.hyper` exists
- validates the file type
- reads Tableau credentials and settings from environment variables
- signs in using a Tableau Personal Access Token (PAT)
- overwrites the configured datasource
- pings the Tableau view `EligibilityData-DQMetrics/DataQualityMetrics?:refresh=y` to trigger refresh

NOTE: PAT credentials must be set as GitHub secrets for the workflow, and as environment variables for local testing.


---

### Repository structure

The GitHub Actions workflow expects the scripts to exist at:

```text
scripts/tableau/generate_tableau_data.py
scripts/tableau/tableau_refresh.py
```

because it runs:

```yaml
python scripts/tableau/generate_tableau_data.py
python scripts/tableau/tableau_refresh.py
```

---

### Running locally

### Prerequisites

You will need:

- Python 3.13 recommended, to match the workflow setup.
- Access to AWS with permission to read from the S3 bucket `eligibility-signposting-api-dev-dq-metrics`.
- Tableau Personal Access Token credentials
- The required Python packages installed:
  - `boto3`
  - `pandas`
  - `tableauserverclient`
  - `tableauhyperapi`
  - `requests`

#### Install dependencies

If installing dependencies locally

```bash
pip install boto3 pandas tableauserverclient tableauhyperapi requests
```

#### Required environment variables

Before publishing to Tableau, set the following environment variables:

```bash
export TABLEAU_TOKEN_NAME="your-token-name"
export TABLEAU_TOKEN_VALUE="your-token-value"
export TABLEAU_SERVER_URL="https://your-tableau-server"
export TABLEAU_DATASOURCE_ID="your-datasource-id"
export TABLEAU_SITE_ID="NHSD_DEV"
```

`TABLEAU_SERVER_URL` is the base URL of the Tableau Server instance, for example `https://tableau.nhsd.com`.

`TABLEAU_DATASOURCE_ID` is the ID of the datasource to overwrite,
which can be found in the Tableau Server URL when viewing the datasource (LUID).

`TABLEAU_SITE_ID` defaults to `NHSD_DEV` if not set.

#### AWS credentials

You also need AWS credentials available locally so `boto3` can read from S3.
Also, may need to set the AWS region if not configured globally:

```bash
export AWS_REGION=eu-west-2
```

The workflow uses `eu-west-2`.

#### Run the scripts

Step 1: Generate the Hyper file

```bash
python scripts/tableau/generate_tableau_data.py
```

This should create:

```text
converted.hyper
```

Step 2: Publish to Tableau

```bash
python scripts/tableau/tableau_refresh.py
```

If you want the publish step to continue even when the cache refresh ping fails:

```bash
python scripts/tableau/tableau_refresh.py --ignore-refresh-failure
```

The optional `--ignore-refresh-failure` flag prevents the script from exiting with an error
if the Tableau refresh ping fails.

---

### Expected local flow

1. Read recent DQ metric JSON data from S3
2. Build `converted.hyper`
3. Sign in to Tableau using PAT credentials
4. Overwrite the target datasource
5. Trigger cache refresh for the relevant workbook view

---



## GitHub Actions workflow

The GitHub Actions workflow is named:

```yaml
Daily Tableau Data Update
```

It supports:

- scheduled execution every day at `10:00 AM UTC`
- manual triggering using `workflow_dispatch` for testing

### Workflow triggers

```yaml
on:
  schedule:
    - cron: '0 10 * * *'
  workflow_dispatch:
```

### Workflow jobs

The workflow has two jobs:

### 1. `metadata`

This job:

- checks out the repo
- reads versions from `.tool-versions`
- sets CI metadata such as build timestamp and version string

### 2. `publish`

This job:

- sets up Python 3.13
- checks out the repository
- installs the required Python packages
- assumes the AWS deployment role using GitHub OIDC
- runs the S3 to Hyper script
- publishes the datasource to Tableau

---

## GitHub Actions secrets and variables

The workflow requires the following GitHub environment configuration.

### Secrets

- `AWS_ACCOUNT_ID`
- `TABLEAU_TOKEN_NAME`
- `TABLEAU_TOKEN_VALUE`
- `TABLEAU_DATASOURCE_ID`

### Variables

- `TABLEAU_SITE_ID`
- `TABLEAU_SERVER_URL`

### GitHub environment

The workflow runs under the `dev` environment.

---

## Example GitHub Actions execution flow

```text
Schedule or manual trigger
  -> metadata job
  -> publish job
      -> setup Python
      -> install dependencies
      -> assume AWS role
      -> generate converted.hyper from S3 JSON files
      -> publish converted.hyper to Tableau datasource
      -> trigger Tableau cache refresh
```

---

## Troubleshooting

### `Datasource file not found: ./converted.hyper`

The publish script expects `converted.hyper` to exist in the current working directory. Run the data generation script first.

### `Missing required environment variables`

Ensure the required Tableau environment variables are set before running `tableau_refresh.py`.

### No data found

If no JSON files are found for the date range, the generation script will print:

```text
No data found for the selected date range.
```

and no Hyper file will be created.

### Cache refresh fails

By default, a Tableau cache refresh failure causes the script to exit with a non zero status. Use:

```bash
python scripts/tableau/tableau_refresh.py --ignore-refresh-failure
```

if you want to allow publish success even when the refresh ping fails.
