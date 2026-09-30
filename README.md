# 8Manager actions

Reusable GitHub Actions workflows that run 8Manager's scans **in your repository's own CI** and post the
results to 8Manager. They are non-blocking (an 8Manager outage never fails your build) and authenticate
with GitHub OIDC — no secret is added to your repository.

| Workflow | What it does |
|---|---|
| `8manager-security.yml` | Trivy (dependencies, IaC misconfiguration, secrets) + Opengrep (SAST), optional Polaris |
| `8manager-quality.yml` | Complexity (lizard) + duplication (jscpd), weighted by 90-day churn |
| `8manager-structure.yml` | Semantic duplication + dead code (Tree-sitter); posts derived findings only, never source |

You normally don't add these by hand: the 8Manager app generates `.github/workflows/8manager-scan.yml`
for each repository (Security / Code quality pages → Set up scan).

```yaml
permissions:
  id-token: write
  contents: read
jobs:
  security:
    uses: hugofe/8manager-actions/.github/workflows/8manager-security.yml@main
  quality:
    uses: hugofe/8manager-actions/.github/workflows/8manager-quality.yml@main
  structure:
    uses: hugofe/8manager-actions/.github/workflows/8manager-structure.yml@main
```
