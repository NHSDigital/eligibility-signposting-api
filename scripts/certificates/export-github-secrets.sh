#!/bin/bash
#
# Export certificates to GitHub Secrets format
#
# This script exports the generated certificates in the exact format
# expected by your GitHub secrets (API_CA_CERT, API_CLIENT_CERT, API_PRIVATE_KEY_CERT)
#
# Usage: ./export-github-secrets.sh [environment] [output-format]
# Example: ./export-github-secrets.sh dev json
#          ./export-github-secrets.sh dev env

set -euo pipefail

ENVIRONMENT=${1:-dev}
OUTPUT_FORMAT=${2:-json}
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

# Check if certificates exist
check_certificates() {
    local required_files=(
        "${CERTS_DIR}/combined/certificate.pem"
        "${CERTS_DIR}/combined/private-key.pem"
        "${CERTS_DIR}/combined/certificate-chain.pem"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required certificate file not found: $file"
            log_error "Please run generate-certificates.sh first"
            exit 1
        fi
    done
}

# Convert certificate to single-line format for JSON/environment variables
format_certificate() {
    local file="$1"
    # Replace newlines with \n and escape any existing backslashes
    sed ':a;N;$!ba;s/\n/\\n/g' "$file" | sed 's/\\/\\\\/g'
}

# Export in JSON format (for GitHub API or configuration files)
export_json_format() {
    log_info "Exporting certificates in JSON format..."

    local api_ca_cert=$(format_certificate "${CERTS_DIR}/combined/certificate-chain.pem")
    local api_client_cert=$(format_certificate "${CERTS_DIR}/combined/certificate.pem")
    local api_private_key_cert=$(format_certificate "${CERTS_DIR}/combined/private-key.pem")

    cat > "${CERTS_DIR}/github-secrets.json" << EOF
{
  "API_CA_CERT": "${api_ca_cert}",
  "API_CLIENT_CERT": "${api_client_cert}",
  "API_PRIVATE_KEY_CERT": "${api_private_key_cert}"
}
EOF

    log_info "✓ JSON format exported to: ${CERTS_DIR}/github-secrets.json"
}

# Export in environment variable format (for .env files or direct copy-paste)
export_env_format() {
    log_info "Exporting certificates in environment variable format..."

    local api_ca_cert=$(format_certificate "${CERTS_DIR}/combined/certificate-chain.pem")
    local api_client_cert=$(format_certificate "${CERTS_DIR}/combined/certificate.pem")
    local api_private_key_cert=$(format_certificate "${CERTS_DIR}/combined/private-key.pem")

    cat > "${CERTS_DIR}/github-secrets.env" << EOF
API_CA_CERT="${api_ca_cert}"
API_CLIENT_CERT="${api_client_cert}"
API_PRIVATE_KEY_CERT="${api_private_key_cert}"
EOF

    log_info "✓ Environment format exported to: ${CERTS_DIR}/github-secrets.env"
}

# Export individual files (for manual copy-paste)
export_individual_files() {
    log_info "Creating individual secret files..."

    mkdir -p "${CERTS_DIR}/secrets"

    format_certificate "${CERTS_DIR}/combined/certificate-chain.pem" > "${CERTS_DIR}/secrets/API_CA_CERT.txt"
    format_certificate "${CERTS_DIR}/combined/certificate.pem" > "${CERTS_DIR}/secrets/API_CLIENT_CERT.txt"
    format_certificate "${CERTS_DIR}/combined/private-key.pem" > "${CERTS_DIR}/secrets/API_PRIVATE_KEY_CERT.txt"

    log_info "✓ Individual secret files created in: ${CERTS_DIR}/secrets/"
}

# Display GitHub Actions setup instructions
display_github_actions_instructions() {
    log_info "GitHub Actions Setup Instructions:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    log_detail "Option 1: Using GitHub CLI (recommended)"
    echo "gh secret set API_CA_CERT --body \"\$(cat ${CERTS_DIR}/secrets/API_CA_CERT.txt)\""
    echo "gh secret set API_CLIENT_CERT --body \"\$(cat ${CERTS_DIR}/secrets/API_CLIENT_CERT.txt)\""
    echo "gh secret set API_PRIVATE_KEY_CERT --body \"\$(cat ${CERTS_DIR}/secrets/API_PRIVATE_KEY_CERT.txt)\""
    echo
    log_detail "Option 2: Manual GitHub UI"
    echo "1. Go to your repository → Settings → Secrets and variables → Actions"
    echo "2. Click 'New repository secret' for each secret:"
    echo "   - Name: API_CA_CERT"
    echo "     Value: Copy from ${CERTS_DIR}/secrets/API_CA_CERT.txt"
    echo "   - Name: API_CLIENT_CERT"
    echo "     Value: Copy from ${CERTS_DIR}/secrets/API_CLIENT_CERT.txt"
    echo "   - Name: API_PRIVATE_KEY_CERT"
    echo "     Value: Copy from ${CERTS_DIR}/secrets/API_PRIVATE_KEY_CERT.txt"
    echo
    log_detail "Option 3: Using the GitHub API"
    echo "Use the JSON file: ${CERTS_DIR}/github-secrets.json"
    echo "with the GitHub REST API to set secrets programmatically"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Display certificate validation info
display_validation_info() {
    log_info "Certificate Validation:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    log_detail "Certificate Details:"
    echo "Environment: ${ENVIRONMENT}"
    echo "Domain: ${ENVIRONMENT}.eligibility-signposting-api.nhs.uk"

    echo
    log_detail "Client Certificate Expiry:"
    openssl x509 -in "${CERTS_DIR}/combined/certificate.pem" -noout -dates

    echo
    log_detail "CA Certificate Expiry:"
    openssl x509 -in "${CERTS_DIR}/combined/certificate-chain.pem" -noout -dates

    echo
    log_detail "Certificate Chain Validation:"
    if openssl verify -CAfile "${CERTS_DIR}/combined/certificate-chain.pem" "${CERTS_DIR}/combined/certificate.pem" > /dev/null 2>&1; then
        echo "✓ Certificate chain is valid"
    else
        echo "✗ Certificate chain validation failed"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Display next steps
display_next_steps() {
    log_info "Next Steps:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. Set the GitHub secrets using one of the methods above"
    echo "2. Update your GitHub Actions workflow to use the new secrets"
    echo "3. Deploy your infrastructure with the new certificates"
    echo "4. Test the mTLS connectivity"
    echo "5. Set up certificate expiration monitoring"
    echo
    log_warn "Certificate Rotation:"
    echo "• Client/Server certificates expire in 1 year"
    echo "• CA certificate expires in 10 years"
    echo "• Set up calendar reminders for certificate renewal"
    echo "• Consider automating certificate rotation in your CI/CD pipeline"
    echo
    echo "Files created:"
    echo "• JSON format: ${CERTS_DIR}/github-secrets.json"
    echo "• Environment format: ${CERTS_DIR}/github-secrets.env"
    echo "• Individual secrets: ${CERTS_DIR}/secrets/"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    log_info "Exporting mTLS certificates for GitHub Secrets (${ENVIRONMENT} environment)"

    check_certificates

    case "${OUTPUT_FORMAT}" in
        json)
            export_json_format
            ;;
        env)
            export_env_format
            ;;
        all|*)
            export_json_format
            export_env_format
            ;;
    esac

    export_individual_files
    display_validation_info
    display_github_actions_instructions
    display_next_steps

    log_info "Certificate export completed successfully!"
}

# Display usage
usage() {
    echo "Usage: $0 [environment] [format]"
    echo
    echo "Arguments:"
    echo "  environment  Environment name (dev, test, prod) [default: dev]"
    echo "  format       Output format: json, env, all [default: all]"
    echo
    echo "Examples:"
    echo "  $0 dev json         # Export dev certificates in JSON format"
    echo "  $0 prod env         # Export prod certificates as environment variables"
    echo "  $0 test all         # Export test certificates in all formats"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
        usage
        exit 0
    fi

    main "$@"
fi
