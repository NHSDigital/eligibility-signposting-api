#!/bin/bash
#
# Self-Signed Certificate Generation Script for mTLS
# Based on: https://gist.github.com/fntlnz/cf14feb5a46b2eda428e000157447309
#
# This script generates:
# 1. Root CA certificate and key
# 2. Server certificate and key (for external API proxy)
# 3. Client certificate and key (for API Gateway)
#
# Usage: ./generate-certificates.sh [environment]
# Example: ./generate-certificates.sh dev

set -euo pipefail

ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/generated/${ENVIRONMENT}"
DOMAIN="eligibility-signposting-api.nhs.uk"
API_DOMAIN="${ENVIRONMENT}.${DOMAIN}"

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

# Create directory structure
create_directories() {
    log_info "Creating certificate directories for environment: ${ENVIRONMENT}"
    mkdir -p "${CERTS_DIR}"/{ca,server,client,combined}
}

# Generate Root CA
generate_root_ca() {
    log_info "Checking for existing Root CA certificate..."

    # Check if CA certificate and key already exist
    if [[ -f "${CERTS_DIR}/ca/ca.crt" && -f "${CERTS_DIR}/ca/ca.key" ]]; then
        log_info "✓ Found existing Root CA certificate and key - reusing them"
        log_info "CA Certificate: ${CERTS_DIR}/ca/ca.crt"
        log_info "CA Private Key: ${CERTS_DIR}/ca/ca.key"

        # Verify the existing CA certificate is still valid
        if openssl x509 -in "${CERTS_DIR}/ca/ca.crt" -noout -checkend 86400 > /dev/null 2>&1; then
            log_info "✓ Existing Root CA certificate is valid for at least 24 hours"
            return 0
        else
            log_warn "⚠ Existing Root CA certificate expires within 24 hours - regenerating"
        fi
    else
        log_info "No existing Root CA found - generating new certificate"
    fi

    log_info "Generating Root CA certificate and key..."

    # Create CA configuration
    cat > "${CERTS_DIR}/ca/ca.conf" << EOF
[req]
default_bits = 4096
distinguished_name = req_distinguished_name
req_extensions = v3_ca
prompt = no

[req_distinguished_name]
C = GB
ST = West Yorkshire
L = Leeds
O = NHS England
OU = API Management Root CA
CN = NHS England API Management Root CA

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
EOF

    # Generate CA private key
    openssl genrsa -out "${CERTS_DIR}/ca/ca.key" 4096

    # Generate CA certificate
    openssl req -new -x509 -days 3650 -key "${CERTS_DIR}/ca/ca.key" \
        -out "${CERTS_DIR}/ca/ca.crt" \
        -config "${CERTS_DIR}/ca/ca.conf" \
        -extensions v3_ca

    log_info "✓ New Root CA certificate generated: ${CERTS_DIR}/ca/ca.crt"
}

# Generate Server Certificate (for external API proxy)
generate_server_certificate() {
    log_info "Generating server certificate for external API proxy..."

    # Create server configuration
    cat > "${CERTS_DIR}/server/server.conf" << EOF
[req]
default_bits = 4096
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = GB
ST = West Yorkshire
L = Leeds
O = NHS England
OU = API Management
CN = ${API_DOMAIN}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${API_DOMAIN}
DNS.2 = *.${DOMAIN}
EOF

    # Generate server private key
    openssl genrsa -out "${CERTS_DIR}/server/server.key" 4096

    # Generate server certificate request
    openssl req -new -key "${CERTS_DIR}/server/server.key" \
        -out "${CERTS_DIR}/server/server.csr" \
        -config "${CERTS_DIR}/server/server.conf"

    # Sign server certificate with CA
    openssl x509 -req -in "${CERTS_DIR}/server/server.csr" \
        -CA "${CERTS_DIR}/ca/ca.crt" \
        -CAkey "${CERTS_DIR}/ca/ca.key" \
        -CAcreateserial \
        -out "${CERTS_DIR}/server/server.crt" \
        -days 365 \
        -extensions v3_req \
        -extfile "${CERTS_DIR}/server/server.conf"

    log_info "Server certificate generated: ${CERTS_DIR}/server/server.crt"
}

# Generate Client Certificate (for API Gateway)
generate_client_certificate() {
    log_info "Generating client certificate for API Gateway..."

    # Create client configuration
    cat > "${CERTS_DIR}/client/client.conf" << EOF
[req]
default_bits = 4096
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = GB
ST = West Yorkshire
L = Leeds
O = NHS England
OU = API Management Client
CN = ${API_DOMAIN}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

    # Generate client private key
    openssl genrsa -out "${CERTS_DIR}/client/client.key" 4096

    # Generate client certificate request
    openssl req -new -key "${CERTS_DIR}/client/client.key" \
        -out "${CERTS_DIR}/client/client.csr" \
        -config "${CERTS_DIR}/client/client.conf"

    # Sign client certificate with CA
    openssl x509 -req -in "${CERTS_DIR}/client/client.csr" \
        -CA "${CERTS_DIR}/ca/ca.crt" \
        -CAkey "${CERTS_DIR}/ca/ca.key" \
        -CAcreateserial \
        -out "${CERTS_DIR}/client/client.crt" \
        -days 365 \
        -extensions v3_req \
        -extfile "${CERTS_DIR}/client/client.conf"

    log_info "Client certificate generated: ${CERTS_DIR}/client/client.crt"
}

# Create certificate chains for AWS ACM
create_certificate_chains() {
    log_info "Creating certificate chains for AWS ACM..."

    # Create combined client certificate (certificate + CA chain)
    cat "${CERTS_DIR}/client/client.crt" "${CERTS_DIR}/ca/ca.crt" > "${CERTS_DIR}/combined/client-chain.crt"

    # Create truststore (CA certificate for truststore)
    cp "${CERTS_DIR}/ca/ca.crt" "${CERTS_DIR}/combined/truststore.pem"

    # Create PEM files in the format expected by ACM
    cp "${CERTS_DIR}/client/client.crt" "${CERTS_DIR}/combined/certificate.pem"
    cp "${CERTS_DIR}/client/client.key" "${CERTS_DIR}/combined/private-key.pem"
    cp "${CERTS_DIR}/ca/ca.crt" "${CERTS_DIR}/combined/certificate-chain.pem"

    log_info "Certificate chains created in: ${CERTS_DIR}/combined/"
}

# Verify certificates
verify_certificates() {
    log_info "Verifying certificate chain..."

    # Verify client certificate against CA
    if openssl verify -CAfile "${CERTS_DIR}/ca/ca.crt" "${CERTS_DIR}/client/client.crt" > /dev/null 2>&1; then
        log_info "✓ Client certificate verification successful"
    else
        log_error "✗ Client certificate verification failed"
        return 1
    fi

    # Verify server certificate against CA
    if openssl verify -CAfile "${CERTS_DIR}/ca/ca.crt" "${CERTS_DIR}/server/server.crt" > /dev/null 2>&1; then
        log_info "✓ Server certificate verification successful"
    else
        log_error "✗ Server certificate verification failed"
        return 1
    fi
}

# Display certificate information and next steps
display_certificate_info() {
    log_info "Certificate Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Environment: ${ENVIRONMENT}"
    echo "Domain: ${API_DOMAIN}"
    echo "Generated files location: ${CERTS_DIR}"
    echo
    echo "Certificate Files for Manual Use:"
    echo "  Certificate Body:  ${CERTS_DIR}/combined/certificate.pem"
    echo "  Private Key:       ${CERTS_DIR}/combined/private-key.pem"
    echo "  Certificate Chain: ${CERTS_DIR}/combined/certificate-chain.pem"
    echo "  Truststore:        ${CERTS_DIR}/combined/truststore.pem"
    echo
    echo "Certificate Validity:"
    openssl x509 -in "${CERTS_DIR}/client/client.crt" -noout -dates
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Set proper file permissions
set_permissions() {
    log_info "Setting secure file permissions..."
    chmod 600 "${CERTS_DIR}"/**/*.key
    chmod 644 "${CERTS_DIR}"/**/*.crt "${CERTS_DIR}"/**/*.pem
}

# Main execution
main() {
    log_info "Starting mTLS certificate generation for ${ENVIRONMENT} environment"

    create_directories
    generate_root_ca
    generate_server_certificate
    generate_client_certificate
    create_certificate_chains
    verify_certificates
    set_permissions
    display_certificate_info

    log_info "Certificate generation completed successfully!"
    log_warn "Next steps:"
    echo "  1. Manually export GitHub secrets using: ./export-github-secrets.sh ${ENVIRONMENT} all"
    echo "  2. Set GitHub secrets using the exported files"
    echo "  3. Deploy infrastructure via GitHub Actions"
    echo "  4. Test mTLS connectivity"
    echo "  5. Set up certificate expiration monitoring"
}

# Check dependencies
check_dependencies() {
    if ! command -v openssl &> /dev/null; then
        log_error "OpenSSL is required but not installed"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    check_dependencies
    main "$@"
fi
