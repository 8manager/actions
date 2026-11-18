# 8Manager rules

Rules 8Manager adds on top of the pinned community rulesets, loaded by `8manager-security.yml`
from a pinned commit of this repository (`EM_RULES_REF`).

| Path | What it covers |
|---|---|
| `sast/8manager/hardcoded-secret.yaml` | Credential-like literals assigned to secret-named variables/keys (JS/TS/Python) — CWE-798 |
| `sast/8manager/weak-hash.yaml` | MD5 / SHA-1 / RIPEMD-160 via `createHash` — CWE-328 |
| `sast/8manager/insecure-random.yaml` | `Math.random()` producing tokens, keys, nonces, ids — CWE-338 |
| `sast/8manager/cleartext-http.yaml` | `http://` / `ws://` URLs to non-local hosts — CWE-319 |
| `sast/8manager/public-tmp-file.yaml` | Fixed file names in `/tmp`, `/var/tmp`, `/dev/shm` — CWE-377 |
| `sast/8manager/regex-backtracking.yaml` | Regex literals with a repeated group that itself repeats (ReDoS heuristic) — CWE-1333 |
| `secrets/secret-config.yaml` | Generic `password/token/secret = <long literal>` in config files (.env, YAML, JSON, ini) |

Test files are excluded from the SAST rules (fixtures and deliberate cases live there). A secret
finding never carries the matched value: the workflow strips the matched lines before reporting.

Each SAST rule has an annotated test file next to it (`ruleid:` / `ok:`). Run everything with
`rules/test-rules.sh`; CI runs it on every pull request (`.github/workflows/rules-test.yml`).
