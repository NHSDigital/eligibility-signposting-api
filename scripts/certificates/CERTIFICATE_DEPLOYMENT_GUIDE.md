# Certificate Deployment Guide

## Quick Reference for mTLS Certificate Deployment

### 1. Generate Certificates

```bash
# Generate certificates for a specific environment
./generate-certificates.sh <environment>

# Examples:
./generate-certificates.sh dev
./generate-certificates.sh preprod
./generate-certificates.sh prod
```

**Generated files location:** `generated/<environment>/`

---

### 2. GitHub Secrets Configuration

**Export secrets format:**
```bash
./export-github-secrets.sh <environment> all
```

**Required GitHub Secrets:**

| Secret Name | File Location | Content |
|-------------|---------------|---------|
| `API_CA_CERT` | `generated/<env>/secrets/API_CA_CERT.txt` | CA Certificate |
| `API_CLIENT_CERT` | `generated/<env>/secrets/API_CLIENT_CERT.txt` | Client Certificate |
| `API_PRIVATE_KEY_CERT` | `generated/<env>/secrets/API_PRIVATE_KEY_CERT.txt` | Client Private Key |


### 3. Proxygen Secret Configuration

**Command:**

```bash
proxygen secret put \
  --mtls-cert generated/<env>/combined/certificate.pem \
  --mtls-key generated/<env>/combined/private-key.pem \
  int eligibility-signposting-api
```

**Files used:**

- **Certificate:** `generated/<env>/combined/certificate.pem` (Client certificate)
- **Private Key:** `generated/<env>/combined/private-key.pem` (Client private key)

---

### 4. AWS Certificate Manager (ACM)

**Optional - to check certs - Manual Import server certificate to ACM:**

| Field | File Location |
|-------|---------------|
| **Certificate body** | `generated/<env>/server/server.crt` |
| **Private key** | `generated/<env>/server/server.key` |
| **Certificate chain** | `generated/<env>/ca/ca.crt` |

Delete after testing otherwise it will cause issues with deployments (if two certs exist)

**API Gateway Configuration:**

- **Custom Domain Certificate:** Use imported ACM certificate ARN
- **Truststore:** Use existing truststore.pem (no update needed if CA unchanged)

---

### 5. AWS Systems Manager (SSM) Parameters

**If using SSM instead of GitHub Secrets:**

```bash
# Set SSM parameters
aws ssm put-parameter \
  --name "/mtls/<env>/api-ca-cert" \
  --type "SecureString" \
  --value "$(cat generated/<env>/ca/ca.crt)"

aws ssm put-parameter \
  --name "/mtls/<env>/api-client-cert" \
  --type "SecureString" \
  --value "$(cat generated/<env>/client/client.crt)"

aws ssm put-parameter \
  --name "/mtls/<env>/api-private-key" \
  --type "SecureString" \
  --value "$(cat generated/<env>/client/client.key)"
```

**Parameter mapping:**

- **CA Certificate:** `generated/<env>/ca/ca.crt`
- **Client Certificate:** `generated/<env>/client/client.crt`
- **Client Private Key:** `generated/<env>/client/client.key`

---

### 6. Testing mTLS Connection

```bash
curl --cert generated/<env>/combined/certificate.pem \
     --key generated/<env>/combined/private-key.pem \
     --cacert generated/<env>/combined/truststore.pem \
     -X GET "https://<env>.eligibility-signposting-api.nhs.uk/patient-check/1" \
     -H "nhs-login-nhs-number:1"
```

---

### 7. File Summary

| Purpose | File Location | Description |
|---------|---------------|-------------|
| **ACM Import** | `server/server.crt` + `server/server.key` + `ca/ca.crt` | Server cert for API Gateway |
| **GitHub/SSM Secrets** | `client/client.crt` + `client/client.key` + `ca/ca.crt` | Client auth certificates |
| **Proxygen Upload** | `combined/certificate.pem` + `combined/private-key.pem` | Client cert for external service |
| **Testing** | `combined/certificate.pem` + `combined/private-key.pem` + `combined/truststore.pem` | mTLS testing |

---

### 8. Important Notes

- **CA Reuse:** Script automatically reuses existing CA certificates when regenerating
- **Truststore:** No update needed in API Gateway if CA unchanged
- **Security:** Never commit `generated/` directory (already in .gitignore)
- **Expiry:** Client/Server certificates expire in 1 year, CA in 10 years
- **Domains:** Certificates are environment-specific (dev/preprod/prod)
