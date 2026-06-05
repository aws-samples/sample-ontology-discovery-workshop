# OntoForge Threat Model

Method: STRIDE, focused on the local workshop app and Neptune handoff artifacts.

## Assets

* Customer domain concepts, relationships, and example data.
* Workshop conversation feed and verified queries.
* `workshop.kuzu` local database.
* `exports/` reports, snapshots, and Neptune load files.
* `ANTHROPIC_API_KEY` when optional LLM extraction is enabled.

## Threats and Mitigations

| Threat | Risk | Mitigation |
| --- | --- | --- |
| Spoofed WebSocket client | Unauthorized viewer receives live graph updates | Optional `ONTOFORGE_TOKEN`, origin validation, local bind address |
| Cypher injection through entity or relation names | DDL/query manipulation | Strict identifier allowlist before Cypher construction |
| User query modifies graph | Data tampering or destructive commands | Read-only query validator rejects write/DDL keywords |
| Path traversal during export | File overwrite outside project | Export path validation restricts writes to `./exports` |
| External CDN script tampering | Browser compromise | Cytoscape is served from `static/vendor` |
| Optional third-party LLM data leakage | Customer data sent outside local environment | `ANTHROPIC_API_KEY` opt-in only, masking guidance, input length limit, legal/security review requirement |
| Local file disclosure | Sensitive workshop data stored on disk | Local filesystem encryption recommended, export files set to `0600`, data retention procedure in `DATA_CLASSIFICATION.md` |
| Neptune export misuse | Customer data loaded into wrong account or public bucket | `docs/NEPTUNE_SECURITY.md` least-privilege IAM, S3 encryption, VPC endpoint, and audit guidance |

## Residual Risk

OntoForge remains a workshop/PoC tool, not a production multi-user ontology platform. Multi-user auth, RBAC, centralized audit retention, and managed encryption are required before operating it as a shared service.
