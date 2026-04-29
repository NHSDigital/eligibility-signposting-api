# Opus 4.6 Assessment Prompt: GitHub Actions Security Best Practices

Use this prompt with Opus 4.6 to assess your GitHub Actions workflows for compliance with NHSDigital best practices.

---

**Prompt:**

Please assess our GitHub Actions workflows for compliance with the NHSDigital GitHub Actions Security Best Practices (see docs/github-actions-best-practices.md).

- Review all workflow files in .github/workflows/ (`*.yml`, `*.yaml`).
- Identify any gaps or violations, including but not limited to:
  - Actions not pinned to commit SHAs
  - Missing or overly broad permissions blocks
  - Use of third-party actions without documentation or justification
  - Secrets handling issues (e.g., secrets exposed, not using GitHub Secrets)
  - Missing dependency scanning or update automation
  - Runner security issues
  - Pull request workflow security (e.g., secrets exposed to forks)
  - OIDC integration and claim limitations
  - Missing audit, monitoring, or CODEOWNERS controls

Please provide:

1. An investigation writeup summarizing the current state and any risks.
2. A list of remediation tickets for each gap found, with suggested actions.

---
