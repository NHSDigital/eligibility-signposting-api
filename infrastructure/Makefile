###################
##   Utilities   ##
###################
guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Variable $* not set"; \
		exit 1; \
	fi

###################
#### Terraform ####
###################

# Initializes the Terraform configuration for the specified stack and environment.
terraform-init: guard-env guard-stack
	rm -rf ./stacks/$(stack)/.terraform
	terraform -chdir=./stacks/$(stack) init -backend-config=backends/$(env).$(stack).tfbackend -upgrade
	terraform -chdir=./stacks/$(stack) get -update

# Selects or creates a Terraform workspace for the specified stack and environment.
terraform-workspace: guard-env guard-stack guard-workspace
	terraform -chdir=./stacks/$(stack) workspace select $(workspace)  || \
	terraform -chdir=./stacks/$(stack) workspace new $(workspace)

	terraform -chdir=./stacks/$(stack) workspace show

# Lists all Terraform workspaces for the specified stack and environment.
terraform-workspace-list: guard-env guard-stack terraform-init
	terraform -chdir=./stacks/$(stack) workspace list

# Deletes a specified Terraform workspace for the stack, switching to the default workspace first.
terraform-workspace-delete: guard-env guard-stack
	terraform -chdir=./stacks/$(stack) workspace select default
	terraform -chdir=./stacks/$(stack) workspace delete $(workspace)

# Runs a specified Terraform command (e.g., plan, apply) for the stack and environment.
terraform: guard-env guard-stack guard-tf-command terraform-init terraform-workspace
	terraform -chdir=./stacks/$(stack) $(tf-command) $(args) -var="environment=$(env)" \
		$(if $(filter init,$(tf-command)),,--parallelism=30) \
		$(if $(filter apply,$(tf-command)),-auto-approve)
	rm -f ./terraform_outputs_$(stack).json || true
	mkdir -p ./build
	terraform -chdir=./stacks/$(stack) output -json > ./build/terraform_outputs_$(stack).json

terraform-as-github: SHELL=/bin/bash
terraform-as-github: guard-env guard-stack guard-tf-command
	@role=$$( [ "$(stack)" = "iams-developer-roles" ] && \
		echo arn:aws:iam::448049830832:role/service-roles/github-actions-iam-bootstrap-role || \
		echo arn:aws:iam::448049830832:role/service-roles/github-actions-api-deployment-role ); \
	read AK SK ST <<< $$(aws sts assume-role --role-arn $$role --role-session-name local \
		--query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text); \
	export AWS_ACCESS_KEY_ID=$$AK AWS_SECRET_ACCESS_KEY=$$SK AWS_SESSION_TOKEN=$$ST; \
	echo "Caller identity after assume-role:"; \
	aws sts get-caller-identity; \
	d=./stacks/$(stack); \
	terraform -chdir=$$d init -backend-config=backends/$(env).$(stack).tfbackend -upgrade; \
	terraform -chdir=$$d get -update; \
	terraform -chdir=$$d $(tf-command) $(args) -var="environment=$(env)" \
		$$( [ "$(tf-command)" != "init" ] && echo --parallelism=30 ) \
		$$( [ "$(tf-command)" = "apply" ] && echo -auto-approve ); \
	mkdir -p build; \
	terraform -chdir=$$d output -json > build/terraform_outputs_$(stack).json

###################
#### Bootstrap ####
###################

# Initializes the Terraform configuration for the bootstrap stack.
bootstrap-terraform-init: guard-env
	terraform -chdir=./stacks/bootstrap init -upgrade
	terraform -chdir=./stacks/bootstrap get -update

# Runs a specified Terraform command (e.g., plan, apply) for the bootstrap stack.
bootstrap-terraform: guard-env guard-tf-command bootstrap-terraform-init
	terraform -chdir=./stacks/bootstrap $(tf-command) $(args) -var="environment=$(env)"
