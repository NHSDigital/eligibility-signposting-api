# Terraform configuration

This file is a placeholder for actual instructions

## Playground instructions

The Terraform can be played with by doing the following:

1. Ensure your poetry environment is up to date: `make install-python`
2. Bring the custom localstack container up: `docker-compose up -d` in root dir.
3. Change dir to the 'local' Terraform environment directory: `cd /infrastructure/environments/local`
4. Initialise Terraform: `poetry run  tflocal init`
5. Validate Terraform: `poetry run tflocal validate`
6. Apply Terraform: `poetry run tflocal apply -auto-approve -var environment=local`
7. You can then interact with the localstack container using the method of your choice.

The initial Terraform:

1. Creates a dynamoDB table with your choice of name.
2. Creates an s3 bucket with your choice of name.
3. Deploys the lambda zip that we build in `/dist/lambda.zip`.
