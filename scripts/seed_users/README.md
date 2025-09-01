# 🧬 DynamoDB Seeder Script

This script deletes and inserts items into a DynamoDB table using JSON seed data. It’s designed for integration testing and local development workflows.
This script is user in the Preprod seed workflow.

---

## 📦 Requirements

- Python 3.13
- AWS credentials configured (via `~/.aws/credentials`, environment variables, or IAM role)
- Required Python packages:

  ```bash
  pip install boto3
  ```

---

## 🚀 Usage

From the project root, run:

```bash
python scripts/seed_users/seed_dynamodb.py \
  --table-name <your-dynamodb-table-name> \
  --region <aws-region> \
  --data-folder <path-to-json-folder>
```

### Example

```bash
python scripts/seed_users/seed_dynamodb.py \
  --table-name eligibility-signposting-api-dev-eligibility_datastore \
  --region eu-west-2 \
  --data-folder tests/e2e/data/dynamoDB/vitaIntegrationTestData
```

---

## 📁 JSON Data Format

Each `.json` file in the specified folder should follow this structure:

```json
{
  "data": [
    {
        "NHS_NUMBER": "1234567890",
        "ATTRIBUTE_TYPE": "COHORTS",
        "otherAttribute1": "value",
        "otherAttribute2": "value"
    }
  ]
}
```

## 🧹 What It Does

1. **Deletes** existing items in the table matching `NHS_NUMBER` from all JSON files.
2. **Inserts** all items from the same files into the table.

---

## 🛡️ Safety Notes

- This script performs destructive operations — do not use this in prod environment.
- Ensure your AWS credentials have appropriate permissions for `dynamodb:DeleteItem` and `dynamodb:PutItem`.

---
