---
lab5_triage:
  image: ghcr.io/whiperr/itsm-svcdesk@sha256:0000000000000000000000000000000000000000000000000000000000000000
  sarif_receipt: 0
---
<!-- ai-generated: 50% - initial triage rows for fixed starlette CVEs -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
One row per rule of one tool; a row may cover several locations, and the Reason says which. Tool is the tool id of
P-15 (`trivy`, `grype`, `osv-scanner`, `gitleaks`, `semgrep`). Decision is one of `fix`, `ignore`,
`false-positive`, `accept`.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2024-47874 | fix | Upgraded starlette from 0.38.6 to >=1.3.1 (via fastapi>=0.135.0) in requirements.txt to patch multipart DoS. |
| trivy | CVE-2026-48818 | fix | Upgraded starlette from 0.38.6 to >=1.3.1 in requirements.txt to fix SSRF and NTLM theft in StaticFiles. |
| trivy | CVE-2026-54283 | fix | Upgraded starlette from 0.38.6 to >=1.3.1 in requirements.txt to enforce request.form() parsing limits. |

## Bake-off

Placeholder to be completed after running bakeoff.py on the revealed canary labels (minimum 600 characters required by P-13).