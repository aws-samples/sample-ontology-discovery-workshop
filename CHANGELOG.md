# Changelog

## v0.1-beta - 2026-06-06

Initial beta release of OntoForge, a local ontology discovery workshop tool.

### Feature Overview

- Live workshop graph: build ontology schemas (T-Box) and instance graphs (A-Box) in a local Kuzu property graph database.
- Real-time browser viewer: visualize entities, relations, instances, and query focus results with Cytoscape.js.
- Agent-oriented workflow: use Claude Code / Kiro skill instructions to structure workshop conversations into graph updates and report inputs.
- Multilingual workshop behavior: keep repository docs and skills in English while responding and generating human-readable workshop content in the user's language.
- Query validation: run read-only openCypher checks against the local graph and record verified customer questions.
- Persistence and restore: reload `workshop.kuzu` on normal restart and restore workshop feed/query state from `exports/session/workshop_snapshot.json`.
- Export package: generate workshop reports, standalone snapshots, Amazon Neptune openCypher scripts, and Bulk Loader CSV files.
- Security baseline: local-only defaults, optional token protection, origin validation, export path restrictions, audit logging, vendored browser dependency, and least-privilege Neptune export guidance.
