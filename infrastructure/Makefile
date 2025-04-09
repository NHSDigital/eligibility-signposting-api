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
	terraform -chdir=./stacks/$(stack) init -var-file=stacks/_shared/tfvars/$(env).tfvars -backend-config=backends/$(env).$(stack).tfbackend -upgrade
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
	terraform -chdir=./stacks/$(stack) $(tf-command) -var-file=../_shared/tfvars/$(env).tfvars $(args) --parallelism=30
	rm -f ./terraform_outputs_$(stack).json || true
	terraform -chdir=./stacks/$(stack) output -json > ./build/terraform_outputs_$(stack).json

###################
#### Bootstrap ####
###################

# Initializes the Terraform configuration for the bootstrap stack.
bootstrap-terraform-init: guard-env
	terraform -chdir=./stacks/bootstrap init -var-file=stacks/_shared/tfvars/$(env).tfvars -upgrade
	terraform -chdir=./stacks/bootstrap get -update

# Runs a specified Terraform command (e.g., plan, apply) for the bootstrap stack.
bootstrap-terraform: guard-env guard-tf-command bootstrap-terraform-init
	terraform -chdir=./stacks/bootstrap $(tf-command) -var-file=../_shared/tfvars/$(env).tfvars $(args)
