#!/bin/bash
#
# Upload mTLS certificates to AWS SSM Parameter Store
#
# This script uploads the generated certificates to AWS SSM Parameter Store
# in the format expected by the existing Terraform infrastructure
#
# Usage: ./upload-certificates.sh [environment] [aws-profile]
# Example: ./upload-certificates.sh dev my-aws-profile

set -euo pipefail

ENVIRONMENT=${1:-dev}
AWS_PROFILE=${2:-""}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/generated/${ENVIRONMENT}/combined"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Set AWS profile if provided
setup_aws_profile() {
    if [[ -n "${AWS_PROFILE}" ]]; then
        export AWS_PROFILE="${AWS_PROFILE}"
        log_info "Using AWS profile: ${AWS_PROFILE}"
    fi
}

# Check if certificates exist
check_certificates() {
    local required_files=(
        "certificate.pem"
        "private-key.pem"
        "certificate-chain.pem"
        "truststore.pem"
    )

    log_info "Checking for required certificate files..."

    for file in "${required_files[@]}"; do
        if [[ ! -f "${CERTS_DIR}/${file}" ]]; then
            log_error "Required certificate file not found: ${CERTS_DIR}/${file}"
            log_error "Please run generate-certificates.sh first"
            exit 1
        fi
    done

    log_info "✓ All required certificate files found"
}

# Upload certificate to SSM Parameter Store
upload_parameter() {
    local param_name="$1"
    local file_path="$2"
    local description="$3"

    log_info "Uploading ${param_name}..."

    aws ssm put-parameter \
        --name "${param_name}" \
        --description "${description}" \
        --value "file://${file_path}" \
        --type "SecureString" \
        --tier "Advanced" \
        --overwrite \
        --no-cli-pager

    if [[ $? -eq 0 ]]; then
        log_info "✓ Successfully uploaded ${param_name}"
    else
        log_error "✗ Failed to upload ${param_name}"
        return 1
    fi
}

# Upload all certificates
upload_certificates() {
    log_info "Uploading certificates to AWS SSM Parameter Store for environment: ${ENVIRONMENT}"

    # Upload CA certificate (truststore)
    upload_parameter \
        "/${ENVIRONMENT}/mtls/api_ca_cert" \
        "${CERTS_DIR}/certificate-chain.pem" \
        "mTLS CA certificate for ${ENVIRONMENT} environment"

    # Upload client certificate
    upload_parameter \
        "/${ENVIRONMENT}/mtls/api_client_cert" \
        "${CERTS_DIR}/certificate.pem" \
        "mTLS client certificate for ${ENVIRONMENT} environment"

    # Upload private key
    upload_parameter \
        "/${ENVIRONMENT}/mtls/api_private_key_cert" \
        "${CERTS_DIR}/private-key.pem" \
        "mTLS private key for ${ENVIRONMENT} environment"
}

# Verify uploads
verify_uploads() {
    log_info "Verifying parameter uploads..."

    local parameters=(
        "/${ENVIRONMENT}/mtls/api_ca_cert"
        "/${ENVIRONMENT}/mtls/api_client_cert"
        "/${ENVIRONMENT}/mtls/api_private_key_cert"
    )

    for param in "${parameters[@]}"; do
        if aws ssm get-parameter --name "${param}" --no-cli-pager > /dev/null 2>&1; then
            log_info "✓ Parameter exists: ${param}"
        else
            log_error "✗ Parameter missing: ${param}"
            return 1
        fi
    done

    log_info "✓ All parameters verified successfully"
}

# Display summary
display_summary() {
    log_info "Certificate Upload Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Environment: ${ENVIRONMENT}"
    echo "AWS Profile: ${AWS_PROFILE:-"default"}"
    echo
    echo "Uploaded SSM Parameters:"
    echo "  /${ENVIRONMENT}/mtls/api_ca_cert         - CA certificate chain"
    echo "  /${ENVIRONMENT}/mtls/api_client_cert     - Client certificate"
    echo "  /${ENVIRONMENT}/mtls/api_private_key_cert - Private key"
    echo
    echo "Next steps:"
    echo "  1. Run Terraform plan to review changes"
    echo "  2. Apply Terraform configuration"
    echo "  3. Test mTLS connectivity"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    log_info "Starting certificate upload to AWS SSM Parameter Store"

    setup_aws_profile
    check_certificates
    upload_certificates
    verify_uploads
    display_summary

    log_info "Certificate upload completed successfully!"
}

# Check dependencies
check_dependencies() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is required but not installed"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity --no-cli-pager > /dev/null 2>&1; then
        log_error "AWS credentials not configured or invalid"
        log_error "Please configure AWS credentials using 'aws configure' or set AWS_PROFILE"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    check_dependencies
    main "$@"
fi
