#!/bin/bash
#
# Complete mTLS Certificate Setup for GitHub Actions Workflow
#
# This script provides a complete end-to-end certificate setup process
# that integrates with your existing GitHub Actions deployment pipeline.
#
# Usage: ./complete-setup.sh [environment] [github-repo]
# Example: ./complete-setup.sh dev NHSDigital/eligibility-signposting-api

set -euo pipefail

ENVIRONMENT=${1:-dev}
GITHUB_REPO=${2:-""}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
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

log_step() {
    echo -e "${BLUE}${BOLD}[STEP]${NC} $1"
}

# Display welcome message
display_welcome() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BOLD}NHS England Eligibility Signposting API${NC}"
    echo -e "${BOLD}mTLS Self-Signed Certificate Setup${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Environment: ${ENVIRONMENT}"
    echo "GitHub Repo: ${GITHUB_REPO:-"Not specified - manual setup required"}"
    echo "Date: $(date)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking Prerequisites"

    local missing_tools=()

    # Check OpenSSL
    if ! command -v openssl &> /dev/null; then
        missing_tools+=("openssl")
    fi

    # Check GitHub CLI (optional)
    if ! command -v gh &> /dev/null; then
        log_warn "GitHub CLI not found - manual secret setup will be required"
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        echo "Please install the missing tools and try again."
        exit 1
    fi

    log_info "✓ All required tools are available"
}

# Step 1: Generate certificates
generate_certificates() {
    log_step "Step 1: Generating Self-Signed Certificates"

    if [[ -f "${SCRIPT_DIR}/generate-certificates.sh" ]]; then
        "${SCRIPT_DIR}/generate-certificates.sh" "${ENVIRONMENT}"
        log_info "✓ Certificates generated successfully"
    else
        log_error "Certificate generation script not found"
        exit 1
    fi
}

# Step 2: Validate certificates
validate_certificates() {
    log_step "Step 2: Validating Certificates"

    if [[ -f "${SCRIPT_DIR}/validate-certificates.sh" ]]; then
        "${SCRIPT_DIR}/validate-certificates.sh" "${ENVIRONMENT}"
        log_info "✓ Certificates validated successfully"
    else
        log_warn "Validation script not found - skipping validation"
    fi
}

# Step 3: Set up GitHub secrets
setup_github_secrets() {
    log_step "Step 3: GitHub Secrets Setup (Manual)"

    local secrets_dir="${SCRIPT_DIR}/generated/${ENVIRONMENT}/secrets"

    if [[ ! -d "$secrets_dir" ]]; then
        log_info "Generating GitHub secrets format..."
        "${SCRIPT_DIR}/export-github-secrets.sh" "${ENVIRONMENT}" "all"
    fi

    log_info "GitHub secrets must be set up manually"
    echo
    echo "Please set the following GitHub repository secrets:"
    echo
    echo "Repository: ${GITHUB_REPO:-"YOUR_REPOSITORY"}"
    echo "Location: Settings → Secrets and variables → Actions"
    echo
    echo "Files with secret values are located in:"
    echo "  ${secrets_dir}/"
    echo
    echo "Secret: API_CA_CERT"
    echo "File: ${secrets_dir}/API_CA_CERT.txt"
    echo
    echo "Secret: API_CLIENT_CERT"
    echo "File: ${secrets_dir}/API_CLIENT_CERT.txt"
    echo
    echo "Secret: API_PRIVATE_KEY_CERT"
    echo "File: ${secrets_dir}/API_PRIVATE_KEY_CERT.txt"
    echo
    echo "Alternatively, you can use the export script directly:"
    echo "  ./export-github-secrets.sh ${ENVIRONMENT} all"
    echo
    echo "Press Enter when you have set up the secrets..."
    read -r
    fi
}

# Step 4: Provide deployment instructions
provide_deployment_instructions() {
    log_step "Step 4: Deployment Instructions"

    echo "Your certificates are now ready for deployment!"
    echo
    echo "Next steps:"
    echo "1. ✅ Certificates generated and validated"
    echo "2. ✅ GitHub secrets configured manually"
    echo "3. 🔄 Deploy your infrastructure:"
    echo "   - Push changes to trigger GitHub Actions, or"
    echo "   - Manually trigger your deployment workflow, or"
    echo "   - Use your existing deployment process"
    echo
    echo "4. 🧪 Test mTLS connectivity after deployment:"
    echo "   curl -X GET https://${ENVIRONMENT}.eligibility-signposting-api.nhs.uk/_status \\"
    echo "        --cert generated/${ENVIRONMENT}/combined/certificate.pem \\"
    echo "        --key generated/${ENVIRONMENT}/combined/private-key.pem \\"
    echo "        --cacert generated/${ENVIRONMENT}/combined/certificate-chain.pem \\"
    echo "        -v"
    echo
    echo "5. 📅 Set up certificate rotation reminders:"
    echo "   - Client/Server certificates expire: $(openssl x509 -in "generated/${ENVIRONMENT}/combined/certificate.pem" -noout -enddate | cut -d'=' -f2)"
    echo "   - Recommended rotation: 11 months from now"
}

# Display certificate information
display_certificate_info() {
    local certs_dir="${SCRIPT_DIR}/generated/${ENVIRONMENT}"

    echo
    log_info "Certificate Information:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo "Environment: ${ENVIRONMENT}"
    echo "Generated: $(date)"
    echo
    echo "Client Certificate Details:"
    openssl x509 -in "${certs_dir}/combined/certificate.pem" -noout -subject -dates
    echo
    echo "Certificate Chain Validation:"
    if openssl verify -CAfile "${certs_dir}/combined/certificate-chain.pem" "${certs_dir}/combined/certificate.pem" > /dev/null 2>&1; then
        echo "✅ Certificate chain is valid"
    else
        echo "❌ Certificate chain validation failed"
    fi

    echo
    echo "Files created:"
    echo "📁 Certificate files: ${certs_dir}/"
    echo "🔐 GitHub secrets: ${certs_dir}/secrets/"
    echo "📄 JSON export: ${certs_dir}/github-secrets.json"
    echo "🔧 Environment export: ${certs_dir}/github-secrets.env"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Cleanup sensitive files (optional)
offer_cleanup() {
    echo
    log_warn "Security Recommendation"
    echo "For enhanced security, you may want to clean up the generated certificate files"
    echo "after confirming the deployment is successful."
    echo
    echo "The GitHub secrets are now stored securely in your repository."
    echo "Local certificate files can be regenerated if needed."
    echo
    echo "Would you like to clean up local certificate files now? (y/N)"
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf "${SCRIPT_DIR}/generated/${ENVIRONMENT}"
        log_info "✓ Local certificate files cleaned up"
        log_warn "Certificates can be regenerated anytime with: ./generate-certificates.sh ${ENVIRONMENT}"
    else
        log_info "Local certificate files retained for reference"
    fi
}

# Display completion message
display_completion() {
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}${BOLD}✅ mTLS Certificate Setup Complete!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo "📚 Documentation: scripts/certificates/MANUAL_CERTIFICATE_GUIDE.md"
    echo "🔄 Certificate Rotation: Run this script again 11 months from now"
    echo "🆘 Support: Check the README files for troubleshooting guidance"
    echo
    echo "Your existing GitHub Actions workflow will automatically use"
    echo "the new certificates on the next deployment."
    echo
}

# Display usage information
usage() {
    echo "Usage: $0 [environment] [github-repo]"
    echo
    echo "Arguments:"
    echo "  environment    Environment name (dev, test, prod) [default: dev]"
    echo "  github-repo    GitHub repository (owner/repo) for automatic secret setup"
    echo
    echo "Examples:"
    echo "  $0 dev                                    # Generate certificates for dev"
    echo "  $0 prod NHSDigital/eligibility-signposting-api  # Full setup for prod"
    echo
    echo "Prerequisites:"
    echo "  - OpenSSL installed"
    echo "  - GitHub CLI installed and authenticated (for automatic secret setup)"
    echo "  - Repository admin access (for setting secrets)"
}

# Main execution
main() {
    if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
        usage
        exit 0
    fi

    display_welcome
    check_prerequisites
    generate_certificates
    validate_certificates
    setup_github_secrets
    display_certificate_info
    provide_deployment_instructions
    offer_cleanup
    display_completion
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
