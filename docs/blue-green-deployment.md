# Blue-Green Deployment Guide

## Overview

This document outlines the blue-green deployment strategy implemented for the Eligibility Signposting API production environment. Blue-green deployment enables zero-downtime deployments, easy rollbacks, and reduced risk through gradual traffic shifting.

## Architecture

### Components

1. **Lambda Aliases**:
   - `blue`: Stable production version
   - `green`: New deployment candidate
   - `production`: Weighted routing between blue and green

2. **API Gateway Integration**: Routes traffic through the `production` alias

3. **CloudWatch Monitoring**: Tracks error rates and performance metrics

4. **Automated Workflows**: GitHub Actions for deployment automation

## Deployment Process

### 1. Initial Green Deployment

```bash
# Deploy new version to green environment (0% traffic)
./scripts/blue-green-deploy.sh deploy-green
```

This will:
- Build the Lambda package
- Publish a new Lambda version
- Update the green alias
- Deploy with 0% traffic to green

### 2. Canary Deployment

```bash
# Perform gradual traffic shift with monitoring
./scripts/blue-green-deploy.sh canary <green_version>
```

Traffic shift schedule:
- **10%** → Monitor for 5 minutes
- **50%** → Monitor for 10 minutes
- **100%** → Monitor for 5 minutes

### 3. Promotion

```bash
# Promote successful green deployment to blue
./scripts/blue-green-deploy.sh promote <green_version>
```

### 4. Rollback (if needed)

```bash
# Immediate rollback to blue environment
./scripts/blue-green-deploy.sh rollback
```

## Manual Traffic Control

For fine-grained control over traffic distribution:

```bash
# Shift specific percentage to green
./scripts/blue-green-deploy.sh shift-traffic <blue_percentage> <green_version>

# Examples:
./scripts/blue-green-deploy.sh shift-traffic 80 "5"  # 20% to green
./scripts/blue-green-deploy.sh shift-traffic 0 "5"   # 100% to green
```

## GitHub Actions Workflows

### Standard Deployment (Non-Production)
Use existing `cicd-3-deploy.yaml` for dev/test environments.

### Blue-Green Production Deployment
New workflow: `blue-green-deploy.yaml`

**Manual Trigger Options**:
- `deploy-green`: Deploy to green environment
- `shift-traffic-10`: Move 10% traffic to green
- `shift-traffic-50`: Move 50% traffic to green
- `shift-traffic-100`: Move 100% traffic to green
- `rollback-to-blue`: Emergency rollback

## Monitoring and Alerting

### CloudWatch Alarms

1. **Error Rate Monitoring**:
   - Blue environment error threshold: 5 errors/minute
   - Green environment error threshold: 5 errors/minute

2. **SNS Notifications**: Alerts sent to deployment team

### Health Checks

Automated health checks run at each traffic shift:
- API status endpoint validation
- Response time verification
- Error rate monitoring

## Configuration

### Terraform Variables

```hcl
# Traffic distribution (0-100)
blue_traffic_weight = 100

# Lambda versions
blue_lambda_version  = "3"
green_lambda_version = "4"

# Enable/disable blue-green (prod only)
environment = "prod"  # Automatically enables blue-green
```

### Environment-Specific Behavior

- **Production**: Full blue-green deployment with aliases
- **Dev/Test**: Standard direct deployment (no blue-green)

## Safety Features

### 1. Automatic Rollback Triggers
- Error rate exceeds threshold
- Health check failures
- Manual intervention required

### 2. Gradual Traffic Shifting
- Never shift 100% traffic immediately
- Monitor at each step
- Validate before proceeding

### 3. Version Tracking
- All deployments tagged with semantic versioning
- Clear audit trail of what's deployed where

## Best Practices

### Pre-Deployment Checklist
- [ ] All tests passing in CI/CD
- [ ] Green environment health checks pass
- [ ] Monitoring dashboards reviewed
- [ ] Rollback plan confirmed

### During Deployment
- [ ] Monitor CloudWatch metrics continuously
- [ ] Validate each traffic shift step
- [ ] Keep communication channels open
- [ ] Document any issues

### Post-Deployment
- [ ] Validate 100% traffic on new version
- [ ] Promote green to blue
- [ ] Update documentation
- [ ] Clean up old versions

## Troubleshooting

### Common Issues

1. **Health Check Failures**
   ```bash
   # Check API status
   curl -v https://prod.your-api-domain.com/_status

   # Review Lambda logs
   aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/eligibility"
   ```

2. **High Error Rates**
   ```bash
   # Immediate rollback
   ./scripts/blue-green-deploy.sh rollback

   # Review CloudWatch metrics
   aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors
   ```

3. **Traffic Not Shifting**
   ```bash
   # Verify alias configuration
   aws lambda get-alias --function-name eligibility_signposting_api --name production

   # Check Terraform state
   cd infrastructure
   terraform show | grep lambda_alias
   ```

## Emergency Procedures

### Immediate Rollback
If critical issues are detected:

1. Execute immediate rollback:
   ```bash
   ./scripts/blue-green-deploy.sh rollback
   ```

2. Verify rollback success:
   ```bash
   curl https://prod.your-api-domain.com/_status
   ```

3. Notify team and investigate issues

### Contact Information
- **Primary**: DevOps Team
- **Secondary**: Platform Engineering
- **Emergency**: On-call rotation

## Future Enhancements

1. **Automated Canary Analysis**: AI-driven traffic shift decisions
2. **Multi-Region Blue-Green**: Cross-region deployment strategy
3. **Database Schema Migrations**: Coordinated DB and app deployments
4. **Advanced Monitoring**: Custom business metrics integration

---

*Last Updated: August 13, 2025*
*Version: 1.0*
