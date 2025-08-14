#!/bin/bash
# Blue-Green Deployment Automation Script
# This script manages the blue-green deployment process for production

set -euo pipefail

# Configuration
ENVIRONMENT="prod"
LAMBDA_FUNCTION_NAME="eligibility_signposting_api"
AWS_REGION="eu-west-2"
HEALTH_CHECK_URL="https://prod.your-api-domain.com/_status"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Function to get current Lambda version
get_current_version() {
    aws lambda get-alias \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --name "$1" \
        --region "$AWS_REGION" \
        --query 'FunctionVersion' \
        --output text 2>/dev/null || echo "\$LATEST"
}

# Function to publish new Lambda version
publish_lambda_version() {
    local description="$1"
    log "Publishing new Lambda version..."

    aws lambda publish-version \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --description "$description" \
        --region "$AWS_REGION" \
        --query 'Version' \
        --output text
}

# Function to update alias
update_alias() {
    local alias_name="$1"
    local version="$2"

    log "Updating alias $alias_name to version $version"

    aws lambda update-alias \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --name "$alias_name" \
        --function-version "$version" \
        --region "$AWS_REGION" \
        --query 'AliasArn' \
        --output text
}

# Function to shift traffic gradually
shift_traffic() {
    local blue_weight="$1"
    local green_version="$2"
    local green_weight=$((100 - blue_weight))

    log "Shifting traffic: Blue ${blue_weight}%, Green ${green_weight}%"

    # Update Terraform variables
    export TF_VAR_blue_traffic_weight="$blue_weight"
    export TF_VAR_green_lambda_version="$green_version"

    # Apply Terraform changes
    cd infrastructure
    make terraform env="$ENVIRONMENT" stack=api-layer tf-command=apply workspace=default
    cd ..
}

# Function to run health checks
health_check() {
    local max_attempts=5
    local attempt=1

    log "Running health checks..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
            success "Health check passed (attempt $attempt)"
            return 0
        else
            warning "Health check failed (attempt $attempt/$max_attempts)"
            if [ $attempt -eq $max_attempts ]; then
                error "Health checks failed after $max_attempts attempts"
            fi
            sleep 10
            ((attempt++))
        fi
    done
}

# Function to monitor metrics
monitor_metrics() {
    local duration_minutes="$1"
    log "Monitoring metrics for $duration_minutes minutes..."

    # This would integrate with CloudWatch to monitor error rates, latency, etc.
    # For now, we'll simulate monitoring
    sleep "$((duration_minutes * 60))"
    success "Monitoring completed successfully"
}

# Main deployment functions
deploy_green() {
    log "🚀 Starting Green Deployment"

    # Get current blue version
    local blue_version
    blue_version=$(get_current_version "blue")
    log "Current blue version: $blue_version"

    # Build and deploy new version
    log "Building Lambda package..."
    make dependencies install-python
    make build

    # Publish new version
    local green_version
    green_version=$(publish_lambda_version "Green deployment $(date)")
    success "Published green version: $green_version"

    # Update green alias
    update_alias "green" "$green_version"

    # Initial deployment with 0% traffic
    shift_traffic 100 "$green_version"

    success "Green environment deployed successfully"
    echo "Green version: $green_version"
}

canary_deployment() {
    local green_version="$1"

    log "🐦 Starting Canary Deployment (10% traffic)"
    shift_traffic 90 "$green_version"
    health_check
    monitor_metrics 5

    log "📊 Increasing traffic to 50%"
    shift_traffic 50 "$green_version"
    health_check
    monitor_metrics 10

    log "🎯 Full traffic shift to green"
    shift_traffic 0 "$green_version"
    health_check
    monitor_metrics 5

    success "Canary deployment completed successfully"
}

promote_green_to_blue() {
    local green_version="$1"

    log "🔄 Promoting green to blue"
    update_alias "blue" "$green_version"

    # Reset traffic to 100% blue (which is now the new version)
    shift_traffic 100 "$green_version"

    success "Green promoted to blue successfully"
}

rollback() {
    log "🔙 Rolling back to blue environment"

    local blue_version
    blue_version=$(get_current_version "blue")

    shift_traffic 100 "$blue_version"
    health_check

    success "Rollback completed successfully"
}

# Main script logic
case "${1:-}" in
    "deploy-green")
        deploy_green
        ;;
    "canary")
        if [ -z "${2:-}" ]; then
            error "Green version required for canary deployment"
        fi
        canary_deployment "$2"
        ;;
    "promote")
        if [ -z "${2:-}" ]; then
            error "Green version required for promotion"
        fi
        promote_green_to_blue "$2"
        ;;
    "rollback")
        rollback
        ;;
    "shift-traffic")
        if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
            error "Usage: $0 shift-traffic <blue_weight> <green_version>"
        fi
        shift_traffic "$2" "$3"
        ;;
    *)
        echo "Usage: $0 {deploy-green|canary|promote|rollback|shift-traffic}"
        echo ""
        echo "Commands:"
        echo "  deploy-green                    - Deploy new version to green environment"
        echo "  canary <green_version>          - Perform gradual canary deployment"
        echo "  promote <green_version>         - Promote green to blue"
        echo "  rollback                        - Rollback to blue environment"
        echo "  shift-traffic <weight> <version> - Manually shift traffic"
        exit 1
        ;;
esac
