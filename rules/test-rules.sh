#!/usr/bin/env bash
# Unit tests for 8Manager's own rules. Needs `opengrep` and `trivy` on PATH (same versions the
# security workflow pins). SAST rules use the engine's annotated test files (`ruleid:` / `ok:` next to
# each rule); the secret config is checked against testdata/expected.txt.
set -euo pipefail
cd "$(dirname "$0")"
LC_ALL=C.UTF-8 opengrep test sast/8manager
got=$(trivy fs secrets/testdata --scanners secret --secret-config secrets/secret-config.yaml \
        --format json --quiet | jq -r '.Results[]? | .Target as $t | (.Secrets // [])[] | "\($t):\(.StartLine)"' | sort)
if [ "$got" != "$(sort secrets/testdata/expected.txt)" ]; then
  echo "secret config: unexpected matches"; diff <(echo "$got") <(sort secrets/testdata/expected.txt) || true; exit 1
fi
echo "secret config: ok"
