# mTLS Self-Signed Certificate Management

Complete solution for generating and managing self-signed mTLS certificates for the NHS England Eligibility Signposting API, integrated with GitHub Actions workflow.

## Overview

This solution provides self-signed certificate generation that integrates seamlessly with your existing GitHub Actions deployment pipeline. No changes to Terraform or infrastructure code required.

**Architecture:**
- **Root CA Certificate**: Acts as certificate authority for signing client and server certificates
- **Client Certificate**: Used by API Gateway for client authentication to external APIs
- **Server Certificate**: Used by external API proxy for server authentication
- **GitHub Secrets Integration**: Automatically formats certificates for your existing workflow

## Quick Start Guide

### 1. Generate Certificates

```bash
cd scripts/certificates
./generate-certificates.sh dev
```

This single command:
- ✅ Creates CA, client, and server certificates
- ✅ Validates certificate chain integrity
- ✅ Formats certificates for GitHub secrets
- ✅ Exports in multiple formats for flexibility

### 2. Set GitHub Repository Secrets

**Recommended: GitHub CLI**
```bash
gh secret set API_CA_CERT --body "$(cat generated/dev/secrets/API_CA_CERT.txt)"
gh secret set API_CLIENT_CERT --body "$(cat generated/dev/secrets/API_CLIENT_CERT.txt)"
gh secret set API_PRIVATE_KEY_CERT --body "$(cat generated/dev/secrets/API_PRIVATE_KEY_CERT.txt)"
```

**Alternative: GitHub Web Interface**
1. Navigate to: Repository → Settings → Secrets and variables → Actions
2. Create three new secrets using the content from `generated/dev/secrets/` files:
   - `API_CA_CERT`
   - `API_CLIENT_CERT`
   - `API_PRIVATE_KEY_CERT`

### 3. Deploy (No Changes Required!)

Your existing GitHub Actions workflow automatically uses the updated secrets. Just trigger your normal deployment:
- Push to main branch, or
- Manual workflow dispatch, or
- Your existing deployment process

### 4. Validate (Optional)

```bash
./validate-certificates.sh dev
```

## Detailed Script Reference

### `generate-certificates.sh`

**Purpose:** Complete certificate generation and export pipeline

**Usage:** `./generate-certificates.sh [environment]`

**Features:**
- RSA 4096-bit keys for maximum security
- 1-year validity for client/server certificates
- 10-year validity for CA certificate
- Automatic certificate chain validation
- Multiple export formats
- Secure file permissions

**Example:**
```bash
./generate-certificates.sh prod
```

### `export-github-secrets.sh`

**Purpose:** Convert certificates to GitHub secrets format

**Usage:** `./export-github-secrets.sh [environment] [format]`

**Formats:**
- `json` - JSON format for API automation
- `env` - Environment variable format
- `all` - All formats (default)

**Example:**
```bash
./export-github-secrets.sh dev json
```

### `validate-certificates.sh`

**Purpose:** Comprehensive certificate validation

**Usage:** `./validate-certificates.sh [environment] [aws-profile]`

**Validation:**
- Certificate format and integrity
- Certificate chain validation
- GitHub secrets format compatibility
- Certificate-key pair matching
- Optional: AWS infrastructure validation

**Example:**
```bash
./validate-certificates.sh dev my-aws-profile
```

## Generated File Structure

```
scripts/certificates/generated/dev/
├── ca/
│   ├── ca.crt                    # Root CA certificate
│   ├── ca.key                    # Root CA private key
│   └── ca.conf                   # OpenSSL configuration
├── client/
│   ├── client.crt                # Client certificate
│   ├── client.key                # Client private key
│   └── client.conf               # OpenSSL configuration
├── server/
│   ├── server.crt                # Server certificate
│   ├── server.key                # Server private key
│   └── server.conf               # OpenSSL configuration
├── combined/
│   ├── certificate.pem           # Client certificate (ACM format)
│   ├── private-key.pem          # Private key (ACM format)
│   ├── certificate-chain.pem    # CA certificate (ACM format)
│   └── truststore.pem           # API Gateway truststore
├── secrets/                      # Ready for GitHub secrets
│   ├── API_CA_CERT.txt
│   ├── API_CLIENT_CERT.txt
│   └── API_PRIVATE_KEY_CERT.txt
├── github-secrets.json          # JSON format for automation
└── github-secrets.env           # Environment variable format
```

## Certificate Specifications

### Root CA Certificate
- **Key Size:** 4096-bit RSA
- **Validity:** 10 years
- **Usage:** Certificate signing, CRL signing
- **Subject:** `CN=NHS England API Management Root CA, OU=API Management Root CA, O=NHS England, L=Leeds, ST=West Yorkshire, C=GB`

### Client Certificate (API Gateway)
- **Key Size:** 4096-bit RSA
- **Validity:** 1 year
- **Usage:** Client authentication
- **Subject:** `CN={environment}.eligibility-signposting-api.nhs.uk-client`
- **Extended Key Usage:** Client Authentication

### Server Certificate (External API Proxy)
- **Key Size:** 4096-bit RSA
- **Validity:** 1 year
- **Usage:** Server authentication
- **Subject:** `CN={environment}.eligibility-signposting-api.nhs.uk`
- **Subject Alternative Names:**
  - `{environment}.eligibility-signposting-api.nhs.uk`
  - `*.eligibility-signposting-api.nhs.uk`
- **Extended Key Usage:** Server Authentication

## Certificate Rotation

### Automated Rotation Schedule

**Recommended Schedule:**
- **Client/Server Certificates:** Every 11 months (before 1-year expiry)
- **Root CA Certificate:** Every 9 years (before 10-year expiry)

### Rotation Process

1. **Generate new certificates:**
   ```bash
   ./generate-certificates.sh prod
   ```

2. **Update GitHub secrets:**
   ```bash
   gh secret set API_CA_CERT --body "$(cat generated/prod/secrets/API_CA_CERT.txt)"
   gh secret set API_CLIENT_CERT --body "$(cat generated/prod/secrets/API_CLIENT_CERT.txt)"
   gh secret set API_PRIVATE_KEY_CERT --body "$(cat generated/prod/secrets/API_PRIVATE_KEY_CERT.txt)"
   ```

3. **Deploy via normal process:**
   - GitHub Actions automatically picks up new secrets
   - Terraform applies certificate updates
   - Zero-downtime rotation

4. **Validate deployment:**
   ```bash
   ./validate-certificates.sh prod
   ```

### Rotation Monitoring

Set up calendar reminders:
- **90 days before expiry:** Generate and test new certificates in dev
- **30 days before expiry:** Deploy to production
- **7 days before expiry:** Final validation

## Security Considerations

### Certificate Security
- ✅ Private keys are 4096-bit RSA
- ✅ Files have secure permissions (600 for keys, 644 for certs)
- ✅ GitHub secrets are encrypted at rest
- ✅ Certificates use appropriate key usage extensions

### Operational Security
- 🔒 **Root CA private key:** Store securely offline after certificate generation
- 🔒 **Generated files:** Clean up local certificate files after GitHub secrets upload
- 🔒 **GitHub secrets:** Use repository secrets, not environment secrets for production
- 🔒 **Access control:** Limit repository admin access for secret management

### Production Recommendations
- Use separate certificate chains for different environments
- Consider using AWS Private CA for production (future enhancement)
- Implement certificate expiration monitoring in CloudWatch
- Store Root CA private key in encrypted, offline storage

## Troubleshooting

### Common Issues

**Certificate chain validation fails:**
```bash
# Check certificate chain manually
openssl verify -CAfile generated/dev/ca/ca.crt generated/dev/client/client.crt
```

**GitHub secrets format issues:**
```bash
# Regenerate secrets format
./export-github-secrets.sh dev all
```

**mTLS handshake failures:**
```bash
# Test certificate against API Gateway
curl -X GET https://dev.eligibility-signposting-api.nhs.uk/_status \
     --cert generated/dev/combined/certificate.pem \
     --key generated/dev/combined/private-key.pem \
     --cacert generated/dev/combined/certificate-chain.pem \
     -v
```

### Validation Commands

**Check certificate expiry:**
```bash
openssl x509 -in generated/dev/combined/certificate.pem -noout -dates
```

**Verify certificate chain:**
```bash
openssl verify -CAfile generated/dev/combined/certificate-chain.pem generated/dev/combined/certificate.pem
```

**Check certificate details:**
```bash
openssl x509 -in generated/dev/combined/certificate.pem -text -noout
```

**Test GitHub secrets format:**
```bash
# Verify secrets can be decoded properly
echo -n "$(cat generated/dev/secrets/API_CLIENT_CERT.txt)" | sed 's/\\n/\n/g' | openssl x509 -noout -text
```

## Integration with Existing Infrastructure

### GitHub Actions Integration
Your existing GitHub Actions workflows automatically use the updated secrets:
- ✅ No workflow file changes required
- ✅ No Terraform code changes required
- ✅ Existing deployment pipeline unchanged
- ✅ Secrets are automatically injected into Terraform variables

### AWS Infrastructure Integration
The certificates work with your existing AWS resources:
- ✅ SSM Parameter Store integration via Terraform variables
- ✅ ACM certificate import via existing Terraform resources
- ✅ API Gateway mTLS configuration unchanged
- ✅ S3 truststore configuration unchanged

### Terraform Variable Mapping
```hcl
# These Terraform variables automatically receive the GitHub secrets:
variable "API_CA_CERT"         # ← API_CA_CERT secret
variable "API_CLIENT_CERT"     # ← API_CLIENT_CERT secret
variable "API_PRIVATE_KEY_CERT" # ← API_PRIVATE_KEY_CERT secret
```

## Migration from External Certificates

If you're currently using externally signed certificates, the migration is seamless:

1. **Generate self-signed certificates** (this doesn't affect production yet)
2. **Test in development environment** first
3. **Update GitHub secrets** for production environment
4. **Deploy normally** - Terraform handles the certificate rotation
5. **Validate** the new certificates are working

The infrastructure code remains identical - only the certificate source changes from external CA to self-signed.

## References

- [Original Self-Signed Certificate Gist](https://gist.github.com/fntlnz/cf14feb5a46b2eda428e000157447309)
- [AWS Certificate Manager Documentation](https://docs.aws.amazon.com/acm/latest/userguide/)
- [AWS API Gateway mTLS Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mutual-tls.html)
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [OpenSSL Certificate Management](https://www.openssl.org/docs/man1.1.1/man1/openssl.html)
