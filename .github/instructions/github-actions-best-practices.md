# GitHub Actions Security Best Practices (NHSDigital)

This file is a direct copy of the guidance from the NHSDigital Software Engineering Quality Framework:
https://github.com/NHSDigital/software-engineering-quality-framework/blob/main/practices/actions-best-practices.md

_Last updated: 27 April 2026_

---

# GitHub Actions Security Best Practices

## Introduction
GitHub Actions is a powerful automation tool that enables CI/CD workflows directly within your GitHub repository. Securing your GitHub Actions workflows is crucial to protect your code, secrets, and infrastructure from potential security threats.

This guide outlines best practices for securing your GitHub Actions workflows and minimizing security risks. All actions used in committed workflow definitions must be pinned to a full-length commit SHA.

## Table of Contents
- Secrets Management
- Limiting Permissions
- Third-Party Actions
- Dependency Management
- Runner Security
- Pull Request Workflows
- OIDC Integration
- Audit and Monitoring

## Secrets Management
- Store sensitive data (API tokens, credentials, etc.) as GitHub Secrets
- Never hardcode sensitive values in your workflow files
- Do not use structured data as a secret - this can cause GitHub's secret redaction in logs to fail
- Rotate secrets regularly
- Use environment-specific secrets when possible
- Ensure a secret scanner is deployed as part of your workflows
- Public repositories should enable GitHub Secret Scanner and Push Protection
- Minimize secret scope (limit to specific environments/jobs)
- Avoid exposing secrets in logs (don't echo/print secrets, set debug to false, use masking for dynamic secrets)
- Use robust secrets management tools (Azure Key Vault, AWS Secrets Manager)

## Limiting Permissions
- Use least privilege principle for GITHUB_TOKEN
- Use fine-grained tokens only if GITHUB_TOKEN cannot be used
- Create custom GitHub Apps with limited scopes when possible
- Use repository-scoped tokens instead of org-wide tokens

## Third-Party Actions
- Pin all actions to a commit SHA (with inline tag/version comment)
- Do not use tags or branch references in committed workflow definitions
- Review third-party actions before adoption
- Minimize use of third-party actions; prefer native/reusable/org actions
- Document rationale for third-party actions in docs/ADRs.md or similar
- Prefer actions with clear maintenance history, minimal permissions, and narrow scope
- Only use trusted actions from the GitHub Marketplace
- Consider forking/maintaining your own copy of critical actions
- Keep a record of approval/version reviewed
- Enable Dependabot alerts for GitHub Actions
- Set up a workflow to check for outdated actions

## Dependency Management
- Use dependency scanning tools (e.g., Dependabot)
- Implement automated dependency updates
- Regularly review and update dependencies with security patches

## Runner Security
- Self-hosted runners: use only with private repos, run in isolated environments, update/patch regularly, use network isolation, prefer ephemeral runners
- GitHub-hosted runners: be aware they are reset after each job, clean up sensitive data before job completion, don't store persistent sensitive data in runner env

## Pull Request Workflows
- Don't expose secrets to PR workflows from forks
- Use pull_request_target carefully with read-only permissions
- Enforce branch protection rules
- Require code reviews before merging
- Use status checks to enforce security scans

## OIDC Integration
- Use OpenID Connect for cloud providers instead of long-lived credentials
- Limit OIDC token claims (set specific subject claims, implement additional claim conditions)

## Audit and Monitoring
- Enable audit logging for GitHub Actions usage
- Set up alerts for suspicious activity
- Enforce code reviews for workflow file changes
- Use CODEOWNERS to restrict workflow file modification
- Conduct regular reviews of all workflows
- Update security practices based on emerging threats
- Monitor GitHub security advisories

## Additional Resources
- [GitHub Actions Security Hardening Guide](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [GitHub Security Lab](https://securitylab.github.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Security for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions)

## Conclusion
Securing GitHub Actions requires a multi-layered approach focusing on secrets management, permissions, third-party action vetting, and proper configuration. By following these best practices, you can significantly reduce security risks while still enjoying the full benefits of GitHub Actions automation.

Security is an ongoing process—regularly review and update your security practices to adapt to new threats and challenges.
