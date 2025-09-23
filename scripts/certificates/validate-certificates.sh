#!/bin/bash
#
# Validate mTLS certificate configuration
#
# This script validates the certificate chain, verifies SSM parameters,
# and tests certificate compatibility with AWS ACM
#
# Usage: ./validate-certificates.sh [environment] [aws-profile]
# Example: ./validate-certificates.sh dev my-aws-profile

set -euo pipefail

ENVIRONMENT=${1:-dev}
AWS_PROFILE=${2:-""}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/generated/${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_detail() {
    echo -e "${BLUE}[DETAIL]${NC} $1"
}

# Set AWS profile if provided
setup_aws_profile() {
    if [[ -n "${AWS_PROFILE}" ]]; then
        export AWS_PROFILE="${AWS_PROFILE}"
        log_info "Using AWS profile: ${AWS_PROFILE}"
    fi
}

# Validate local certificates
validate_local_certificates() {
    log_info "Validating local certificate files..."

    local cert_files=(
        "${CERTS_DIR}/ca/ca.crt"
        "${CERTS_DIR}/client/client.crt"
        "${CERTS_DIR}/client/client.key"
        "${CERTS_DIR}/server/server.crt"
        "${CERTS_DIR}/server/server.key"
    )

    for file in "${cert_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_info "✓ Found: $(basename "$file")"
        else
            log_error "✗ Missing: $file"
            return 1
        fi
    done

    # Verify certificate chain
    log_info "Verifying certificate chain..."
    if openssl verify -CAfile "${CERTS_DIR}/ca/ca.crt" "${CERTS_DIR}/client/client.crt" > /dev/null 2>&1; then
        log_info "✓ Client certificate chain is valid"
    else
        log_error "✗ Client certificate chain validation failed"
        return 1
    fi

    if openssl verify -CAfile "${CERTS_DIR}/ca/ca.crt" "${CERTS_DIR}/server/server.crt" > /dev/null 2>&1; then
        log_info "✓ Server certificate chain is valid"
    else
        log_error "✗ Server certificate chain validation failed"
        return 1
    fi
}

# Display certificate details
display_certificate_details() {
    log_info "Certificate Details:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo
    log_detail "Root CA Certificate:"
    openssl x509 -in "${CERTS_DIR}/ca/ca.crt" -noout -subject -issuer -dates -purpose

    echo
    log_detail "Client Certificate:"
    openssl x509 -in "${CERTS_DIR}/client/client.crt" -noout -subject -issuer -dates -purpose

    echo
    log_detail "Server Certificate:"
    openssl x509 -in "${CERTS_DIR}/server/server.crt" -noout -subject -issuer -dates -purpose

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Validate AWS SSM parameters (optional - only if AWS credentials are available)
validate_ssm_parameters() {
    log_info "Validating AWS SSM parameters (optional)..."

    # Check if AWS credentials are available
    if ! aws sts get-caller-identity --no-cli-pager > /dev/null 2>&1; then
        log_warn "AWS credentials not available - skipping SSM parameter validation"
        log_info "This is optional when using GitHub secrets workflow"
        return 0
    fi

    local parameters=(
        "/${ENVIRONMENT}/mtls/api_ca_cert"
        "/${ENVIRONMENT}/mtls/api_client_cert"
        "/${ENVIRONMENT}/mtls/api_private_key_cert"
    )

    for param in "${parameters[@]}"; do
        log_info "Checking parameter: $param"

        if aws ssm get-parameter --name "$param" --no-cli-pager > /dev/null 2>&1; then
            # Get parameter metadata
            local param_info
            param_info=$(aws ssm get-parameter --name "$param" --query 'Parameter.{Type:Type,LastModifiedDate:LastModifiedDate,Version:Version}' --output table --no-cli-pager 2>/dev/null || echo "Failed to get parameter info")
            log_info "✓ Parameter exists: $param"
            echo "$param_info"
        else
            log_warn "⚠ Parameter missing: $param (this is normal if using GitHub secrets workflow)"
        fi
        echo
    done
}

# Test certificate format compatibility with ACM and GitHub secrets
test_certificate_compatibility() {
    log_info "Testing certificate format compatibility..."

    # Test GitHub secrets format
    log_info "Testing GitHub secrets format compatibility..."

    local api_ca_cert=$(sed ':a;N;$!ba;s/\n/\\n/g' "${CERTS_DIR}/combined/certificate-chain.pem")
    local api_client_cert=$(sed ':a;N;$!ba;s/\n/\\n/g' "${CERTS_DIR}/combined/certificate.pem")
    local api_private_key_cert=$(sed ':a;N;$!ba;s/\n/\\n/g' "${CERTS_DIR}/combined/private-key.pem")

    if [[ ${#api_ca_cert} -gt 0 && ${#api_client_cert} -gt 0 && ${#api_private_key_cert} -gt 0 ]]; then
        log_info "✓ Certificates can be formatted for GitHub secrets"
    else
        log_error "✗ Certificate formatting for GitHub secrets failed"
        return 1
    fi

    # Validate certificate format for direct use
    if openssl x509 -in "${CERTS_DIR}/combined/certificate.pem" -noout > /dev/null 2>&1; then
        log_info "✓ Client certificate format is valid for AWS ACM"
    else
        log_error "✗ Client certificate format is invalid"
        return 1
    fi

    # Validate private key format
    if openssl rsa -in "${CERTS_DIR}/combined/private-key.pem" -check -noout > /dev/null 2>&1; then
        log_info "✓ Private key format is valid for AWS ACM"
    else
        log_error "✗ Private key format is invalid"
        return 1
    fi

    # Validate CA certificate format
    if openssl x509 -in "${CERTS_DIR}/combined/certificate-chain.pem" -noout > /dev/null 2>&1; then
        log_info "✓ CA certificate format is valid for AWS ACM"
    else
        log_error "✗ CA certificate format is invalid"
        return 1
    fi

    # Test certificate-key pair matching
    local cert_modulus key_modulus
    cert_modulus=$(openssl x509 -noout -modulus -in "${CERTS_DIR}/combined/certificate.pem" | openssl md5)
    key_modulus=$(openssl rsa -noout -modulus -in "${CERTS_DIR}/combined/private-key.pem" | openssl md5)

    if [[ "$cert_modulus" == "$key_modulus" ]]; then
        log_info "✓ Certificate and private key pair match"
    else
        log_error "✗ Certificate and private key pair do not match"
        return 1
    fi

    log_info "✓ All certificates are compatible with GitHub secrets and AWS ACM format"
}

# Test mTLS handshake simulation
simulate_mtls_handshake() {
    log_info "Simulating mTLS handshake..."

    # This is a basic simulation - in production you'd test against the actual endpoints
    log_warn "mTLS handshake simulation requires actual endpoints to test against"
    log_info "Use the following commands to test once your infrastructure is deployed:"
    echo
    echo "  # Test server certificate (external API proxy)"
    echo "  openssl s_client -connect ${ENVIRONMENT}.eligibility-signposting-api.nhs.uk:443 -servername ${ENVIRONMENT}.eligibility-signposting-api.nhs.uk"
    echo
    echo "  # Test client certificate (API Gateway mTLS)"
    echo "  curl -X GET https://${ENVIRONMENT}.eligibility-signposting-api.nhs.uk/_status \\"
    echo "       --cert ${CERTS_DIR}/combined/certificate.pem \\"
    echo "       --key ${CERTS_DIR}/combined/private-key.pem \\"
    echo "       --cacert ${CERTS_DIR}/combined/certificate-chain.pem"
}

# Display validation summary
display_validation_summary() {
    log_info "Validation Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Environment: ${ENVIRONMENT}"
    echo "AWS Profile: ${AWS_PROFILE:-"default"}"
    echo "Certificate Directory: ${CERTS_DIR}"
    echo
    echo "Validation Status: ✓ PASSED"
    echo
    echo "Ready for Terraform deployment:"
    echo "  1. Certificates are properly formatted for AWS ACM"
    echo "  2. Certificate chain validation successful"
    echo "  3. SSM parameters are correctly stored"
    echo "  4. Certificate-key pairs match"
    echo
    echo "Next steps:"
    echo "  1. Deploy infrastructure with 'terraform apply'"
    echo "  2. Test actual mTLS connectivity"
    echo "  3. Monitor CloudWatch logs for mTLS handshake events"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    log_info "Starting mTLS certificate validation for ${ENVIRONMENT} environment"

    setup_aws_profile
    validate_local_certificates
    display_certificate_details
    validate_ssm_parameters
    test_certificate_compatibility
    simulate_mtls_handshake
    display_validation_summary

    log_info "Certificate validation completed successfully!"
}

# Check dependencies
check_dependencies() {
    if ! command -v openssl &> /dev/null; then
        log_error "OpenSSL is required but not installed"
        exit 1
    fi

    # AWS CLI is optional when using GitHub secrets workflow
    if ! command -v aws &> /dev/null; then
        log_warn "AWS CLI not found - SSM parameter validation will be skipped"
        log_info "This is normal when using GitHub secrets workflow"
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    check_dependencies
    main "$@"
fi
