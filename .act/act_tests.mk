ACT_IMAGE = ghcr.io/nhs-england-tools/github-runner-image:20230909-321fd1e-rt
PREPROD_WORKFLOW  = .github/workflows/cicd-4-preprod-deploy.yaml
JOB       = metadata

# Usage: make act EVENT=.act/workflow_run_preprod.json TRIGGER_TYPE=workflow_run
act-preprod-deploy:
	@if [ -z "$(EVENT)" ]; then \
		echo "Usage: make act EVENT=<path-to-event-json>"; \
		exit 1; \
	fi
	@echo "Running act with event file: $(EVENT)"
	ACT=true act \
		-W $(PREPROD_WORKFLOW) \
		--job $(JOB) \
		--eventpath $(EVENT) \
		-P ubuntu-latest=$(ACT_IMAGE) \
		-s GITHUB_TOKEN="$$GITHUB_TOKEN" \
		-s GH_TOKEN="$$GITHUB_TOKEN" \
		--env GITHUB_REPOSITORY="$$REPO" \
		--env PREPROD_WORKFLOW_ID=182365668 \
		--env GITHUB_EVENT_NAME=$(TRIGGER_TYPE)


#act-dev-deploy:
#	@if [ -z "$(EVENT)" ]; then \
#		echo "Usage: make act EVENT=<path-to-event-json>"; \
#		exit 1; \
#	fi
#	@echo "Running act with event file: $(EVENT)"
#	ACT=true act \
#		-W $(WORKFLOW) \
#		--job $(JOB) \
#		--eventpath $(EVENT) \
#		-P ubuntu-latest=$(ACT_IMAGE) \
#		-s GITHUB_TOKEN="$$GITHUB_TOKEN" \
#		-s GH_TOKEN="$$GITHUB_TOKEN" \
#		--env GITHUB_REPOSITORY="$$REPO" \
#		--env DEV_WORKFLOW_ID=143714547 \
#		--env GITHUB_EVENT_NAME=$(TRIGGER_TYPE)
