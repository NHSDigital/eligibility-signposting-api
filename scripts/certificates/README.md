# mTLS Certificate Management Scripts

This directory contains scripts for generating, exporting, and validating self-signed certificates for mutual TLS (mTLS) authentication between the API Gateway and external API proxies.

## Overview

The solution implements mTLS using self-signed certificates that integrate with your existing GitHub Actions workflow and Terraform infrastructure. The certificates are managed manually and passed through GitHub secrets.

**Key Components:**
- **Root CA Certificate**: Acts as the certificate authority for signing client and server certificates
- **Client Certificate**: Used by API Gateway for client authentication to external APIs
- **Server Certificate**: Used by external API proxy for server authentication
- **GitHub Secrets Integration**: Automatically formats certificates for your existing secrets workflow

## Quick Start

### 1. Generate Certificates

```bash
# Generate certificates for your environment
./generate-certificates.sh dev

# This automatically:
# - Creates CA, client, and server certificates
# - Formats them for GitHub secrets
# - Validates the certificate chain
# - Exports in multiple formats
```

### 2. Set GitHub Secrets

Choose one of these methods to set your repository secrets:

**Option A: Using GitHub CLI (Recommended)**
```bash
gh secret set API_CA_CERT --body "$(cat generated/dev/secrets/API_CA_CERT.txt)"
gh secret set API_CLIENT_CERT --body "$(cat generated/dev/secrets/API_CLIENT_CERT.txt)"
gh secret set API_PRIVATE_KEY_CERT --body "$(cat generated/dev/secrets/API_PRIVATE_KEY_CERT.txt)"
```

**Option B: Manual via GitHub UI**
1. Go to Repository → Settings → Secrets and variables → Actions
2. Create new secrets using the content from `generated/dev/secrets/` files

**Option C: Bulk import via JSON**
Use the generated `github-secrets.json` file with the GitHub API

### 3. Deploy via GitHub Actions

Your existing GitHub Actions workflow will automatically use the new certificate secrets - no changes needed to your deployment pipeline!

### 4. Validate Setup

```bash
# Validate certificates locally
./validate-certificates.sh dev

# Test after deployment (optional - requires AWS credentials)
./validate-certificates.sh dev your-aws-profile
```

## Certificate Configuration

### Root CA Certificate
- **Key Size**: 4096 bits RSA
- **Validity**: 10 years
- **Usage**: Certificate signing, CRL signing
- **Subject**: `CN=NHS England API Management Root CA, OU=API Management Root CA, O=NHS England`

### Client Certificate (API Gateway)
- **Key Size**: 4096 bits RSA
- **Validity**: 1 year
- **Usage**: Client authentication
- **Subject**: `CN={environment}.eligibility-signposting-api.nhs.uk-client`
- **Extended Key Usage**: Client Authentication

### Server Certificate (External API Proxy)
- **Key Size**: 4096 bits RSA
- **Validity**: 1 year
- **Usage**: Server authentication
- **Subject**: `CN={environment}.eligibility-signposting-api.nhs.uk`
- **Subject Alternative Names**: `{environment}.eligibility-signposting-api.nhs.uk`, `*.eligibility-signposting-api.nhs.uk`
- **Extended Key Usage**: Server Authentication

## AWS Integration

### ACM Certificate Import
The certificates are automatically formatted for AWS Certificate Manager (ACM):

- **Certificate Body**: Client certificate in PEM format
- **Private Key**: Client private key in PEM format
- **Certificate Chain**: CA certificate in PEM format

### API Gateway mTLS Configuration
The infrastructure uses:
- **Client Certificate**: Stored in ACM for API Gateway client authentication
- **Truststore**: S3-hosted CA certificate for validating client certificates

## Security Considerations

### File Permissions
The scripts automatically set secure permissions:
- Private keys: `600` (owner read/write only)
- Certificates: `644` (owner read/write, group/others read only)

### Certificate Rotation
Certificates should be rotated regularly:
- **Client/Server certificates**: Every 12 months
- **Root CA certificate**: Every 10 years

To rotate certificates:
1. Generate new certificates with the same script
2. Upload new certificates to SSM
3. Apply Terraform changes
4. Test connectivity

### Production Considerations
- Store the Root CA private key securely and offline after initial certificate generation
- Consider using AWS Private Certificate Authority for production environments
- Implement certificate expiration monitoring
- Use separate CA certificates for different environments

## Troubleshooting

### Common Issues

1. **Certificate chain validation failed**
   - Ensure certificates were signed by the correct CA
   - Check certificate dates and validity periods
   - Verify certificate purposes match intended usage

2. **AWS SSM parameter upload failed**
   - Check AWS credentials and permissions
   - Verify SSM parameter naming matches Terraform expectations
   - Ensure certificate files exist and are readable

3. **mTLS handshake failures**
   - Verify certificate chain is complete
   - Check that client certificate has correct extended key usage
   - Ensure truststore contains the correct CA certificate

### Testing mTLS Connectivity

After deployment, test the mTLS setup:

```bash
# Test client certificate against API Gateway
curl -X GET https://dev.eligibility-signposting-api.nhs.uk/_status \
     --cert generated/dev/combined/certificate.pem \
     --key generated/dev/combined/private-key.pem \
     --cacert generated/dev/combined/certificate-chain.pem \
     -v

# Verify certificate details
openssl s_client -connect dev.eligibility-signposting-api.nhs.uk:443 \
                  -servername dev.eligibility-signposting-api.nhs.uk \
                  -cert generated/dev/combined/certificate.pem \
                  -key generated/dev/combined/private-key.pem \
                  -CAfile generated/dev/combined/certificate-chain.pem
```

### Certificate Information

View certificate details:
```bash
# Client certificate details
openssl x509 -in generated/dev/client/client.crt -text -noout

# Verify certificate chain
openssl verify -CAfile generated/dev/ca/ca.crt generated/dev/client/client.crt

# Check certificate expiration
openssl x509 -in generated/dev/client/client.crt -noout -dates
```

## Integration with Terraform

The certificates integrate with the existing Terraform infrastructure:

1. **Networking Stack** (`infrastructure/stacks/networking/`):
   - Imports certificates from SSM into ACM
   - Creates the imported certificate resource

2. **API Layer Stack** (`infrastructure/stacks/api-layer/`):
   - References the ACM certificate for API Gateway domain
   - Configures mTLS authentication with S3-hosted truststore

The scripts maintain compatibility with the existing SSM parameter structure and Terraform resource names.

## References

- [Self-Signed Certificate Generation Gist](https://gist.github.com/fntlnz/cf14feb5a46b2eda428e000157447309)
- [AWS Certificate Manager User Guide](https://docs.aws.amazon.com/acm/latest/userguide/)
- [AWS API Gateway mTLS Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mutual-tls.html)
- [OpenSSL Certificate Management](https://www.openssl.org/docs/man1.1.1/man1/openssl.html)
