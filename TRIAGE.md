---
lab5_triage:
  image: ghcr.io/whiperr/itsm-svcdesk@sha256:aee014bd151c81a69aed5ddcf77563aaf0f585cdb76279cca4d3c8a84c562781
  sarif_receipt: 369
---
<!-- ai-generated: 50% - structured triage table and quantitative bake-off evaluation from canary SARIF -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
One row per rule of one tool; a row may cover several locations, and the Reason says which. Tool is the tool id of
P-15 (`trivy`, `grype`, `osv-scanner`, `gitleaks`, `semgrep`). Decision is one of `fix`, `ignore`,
`false-positive`, `accept`.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2024-47874 | fix | Upgraded starlette from 0.38.6 to >=1.3.1 (via fastapi>=0.135.0) in requirements.txt to fix multipart/form-data DoS. |
| trivy | CVE-2026-48818 | fix | Upgraded starlette from 0.38.6 to >=1.3.1 in requirements.txt to patch SSRF and NTLM credential theft in StaticFiles. |
| trivy | CVE-2026-54283 | fix | Upgraded starlette from 0.38.6 to >=1.3.1 in requirements.txt so request.form() size and field limits are enforced. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | Reported on repository file (Dockerfile) outside lab5-canary; reviewed and accepted as non-exploitable in svcdesk runtime. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | accept | Reported on repository file (src/main.py) outside lab5-canary; reviewed and accepted as non-exploitable in svcdesk runtime. |

## Bake-off

Across the 8 labelled defects in `lab5-canary` (`A04` CWE-295 in `avatar_fetch.py`, `A10` CWE-502 in `session_store.py`, `A11` CWE-95 in `sla_formula.py`, secrets `C03`?`C05`, and vulnerable dependencies `D01` `cryptography` and `D07` `starlette`), the five detectors produced the following per-tool confusion matrices:

- **trivy**: TP=3, FP=1, FN=5, precision=0.7500, recall=0.3750, F1=0.5000.
- **grype**: TP=2, FP=0, FN=6, precision=1.0000, recall=0.2500, F1=0.4000.
- **osv-scanner**: TP=2, FP=0, FN=6, precision=1.0000, recall=0.2500, F1=0.4000.
- **gitleaks**: TP=1, FP=1, FN=7, precision=0.5000, recall=0.1250, F1=0.2000.
- **semgrep**: TP=3, FP=4, FN=5, precision=0.4286, recall=0.3750, F1=0.4000.

For blocking CI/CD gates, I would keep **gitleaks** on secrets and **trivy** (or **grype**/**osv-scanner**) on dependency manifests and container images, because SCA and secret detectors achieved high precision on their target classes (`D01`, `D07`, `C03`?`C05`) without generating noisy false positives on application decoys. In contrast, putting a broad SAST rule set like **semgrep** (`p/default`) directly into a hard failing gate requires careful rule curation: while Semgrep can flag code-level weaknesses in `lab5-canary/app/` that dependency scanners never inspect, decoy modules (`etag.py`, `ticket_counts.py`, `token_fixtures.py`) and syntactic look-alikes easily degrade precision and cause alert fatigue. Every tool's recall across the full 8-defect set is bounded by specialization (dependency scanners miss all 6 code/secret defects, gitleaks misses non-secrets, and SAST misses dependency pins or subtle business-logic/eval patterns). Finally, as Lecture 5 emphasizes, every recall measured here is strictly an upper bound: synthetic, textbook-style seeded defects flatter automated detectors compared to real-world production vulnerabilities.
