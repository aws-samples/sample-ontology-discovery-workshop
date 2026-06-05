# Security

## Supported Use

OntoForge is a local workshop/PoC tool. Do not expose it as an unauthenticated shared service.

## Local Server Hardening

* Bind to `127.0.0.1`.
* Use TLS for any environment where traffic can be observed.
* Loopback clients are allowed without a token for local workshops.
* Set `ONTOFORGE_TOKEN` for non-loopback clients. Set `ONTOFORGE_REQUIRE_TOKEN=1` only when localhost must also require a token.
* Keep `workshop.kuzu` and `exports/` on an encrypted filesystem such as FileVault, BitLocker, or LUKS.

## Secret Handling

* Store `ANTHROPIC_API_KEY` only in the shell environment or a secret manager.
* Do not paste API keys into workshop notes, reports, or snapshots.
* Rotate keys after sensitive customer workshops.
* For AWS deployments, use AWS Secrets Manager and AWS KMS customer-managed keys.

## Data Handling

* Mask personal, biometric, or regulated data before sending text to an LLM.
* Delete `workshop.kuzu` and `exports/` when retention is no longer required.
* Use [DATA_CLASSIFICATION.md](DATA_CLASSIFICATION.md) to classify workshop artifacts.

## Security Scan Record

Current mitigations added in response to scan `7c0554bd-2de0-4f36-9141-6703f48c21dd`:

* Identifier validation for graph DDL and pattern construction.
* Read-only validation for user-submitted Cypher.
* Export path restriction to `./exports`.
* Optional REST/WebSocket token authentication for non-loopback clients and origin validation.
* Local vendored Cytoscape script instead of external CDN.
* Audit logging for graph operations and exports.
* Architecture, threat model, and Neptune security documentation.

Before external distribution, rerun Bandit/Semgrep/ACAT or the target security scanner and attach the updated scan result to this section.
