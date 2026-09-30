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
    uses: 8manager/actions/.github/workflows/8manager-security.yml@<release-commit-sha>  # vX.Y.Z
  quality:
    uses: 8manager/actions/.github/workflows/8manager-quality.yml@<release-commit-sha>  # vX.Y.Z
  structure:
    uses: 8manager/actions/.github/workflows/8manager-structure.yml@<release-commit-sha>  # vX.Y.Z
```

## Versioning

Releases are tagged `vX.Y.Z`, with a moving `v1` tag for the latest 1.x. The 8Manager app pins the
generated workflow to a release **commit SHA** (with the version in a comment), so nothing changes in
your CI until you merge an update — Dependabot (`github-actions` ecosystem) opens those PRs for you.
Never reference `@main`. The workflows pin their own tools too (Trivy, Opengrep, Polaris and the
structure analyzer are version-pinned and checksum-verified).
