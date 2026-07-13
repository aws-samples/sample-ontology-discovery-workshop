# Changelog

## Unreleased

### Added

- Added AI-ODLC workflow design documentation for a one-day AI-guided ontology discovery lifecycle.
- Added server-side AI-ODLC workflow state for claims, user stories, domain events, competency questions, model candidates, data sources, field mappings, validation query seeds, RDF decisions, risks, assumptions, decisions, review findings, action items, gates, and coverage.
- Added workflow REST endpoints for workflow state, claims, stories, events, questions, model candidates, data sources, mappings, validation queries, RDF decisions, reviews, next questions, gates, and coverage.
- Added deterministic /workflow/answer extraction, evidence-aware next-question generation, and automatic adversarial review generation.
- Added workflow state to autosave snapshots, import/restore, standalone snapshot HTML, report generation, and the interactive browser AI-ODLC cockpit panel.
- Added RDF/SHACL handoff exports with Turtle, JSON-LD, SHACL seed shapes, SPARQL seed queries, and RDF mapping notes.
- Updated Claude/Kiro workshop skill instructions to drive workshops through AI-ODLC workflow evidence and gates.

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
