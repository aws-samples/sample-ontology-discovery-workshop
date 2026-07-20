# Changelog

## Unreleased

### Added

- Added AI-ODLC workflow design documentation for a one-day AI-guided ontology discovery lifecycle.
- Added server-side AI-ODLC workflow state for claims, user stories, domain events, competency questions, model candidates, data sources, field mappings, validation query seeds, RDF decisions, risks, assumptions, decisions, review findings, action items, gates, and coverage.
- Added workflow REST endpoints for workflow state, claims, stories, events, questions, model candidates, data sources, mappings, validation queries, RDF decisions, assumptions, contradictions, findings, risks, actions, reviews, item decisions, next questions, gates, and coverage.
- Added deterministic /workflow/answer extraction, evidence-aware next-question generation, and automatic adversarial review generation.
- Added openCypher query verification evidence tracking for workflow validation query seeds.
- Added workflow state to autosave snapshots, import/restore, standalone snapshot HTML, report generation, and the interactive browser AI-ODLC cockpit panel with detailed evidence cards.
- Added RDF/SHACL handoff exports with Turtle, JSON-LD, SHACL seed shapes, SPARQL seed queries, RDF mapping notes, and Neptune RDF follow-up notes.
- Added a user-triggered, latest-result-only RDF/SPARQL/SHACL static validation loop with cockpit/API controls, workflow evidence, reports, and no polling or automatic retry.
- Updated Claude/Kiro workshop skill instructions to drive workshops through AI-ODLC workflow evidence and gates.
- Enforced current-stage answers and sequential-only workflow advancement; forced next-stage transitions now require and audit a reason.
- Replaced count-based workflow gates with predicate-level evidence quality, traceability, review disposition, competency-query coverage, and RDF handoff checks.
- Added contradictions, explicit review decisions, before/after history, owner-linked high-risk acceptance, and conflict-preserving merge proposals.
- Expanded bounded adversarial review to ambiguity, contradiction, unsupported causality, event modeling, over-modeling, and sensitivity checks with source freshness.
- Rebuilt the responsive browser cockpit around Stories, Events, Questions, Model, Data, Review, and Actions panels, with gate drill-down, validation report links, graph uncertainty states, request locking, and accessible status/focus behavior.
- Hardened exact query evidence against missing-question, alias-only answer-shape, comment, string, and `RETURN 1` bypasses; separated query, RDF-validation, and handoff fingerprints.
- Required real discovery-story references, full T-Box review freshness, complete artifact manifests, edge uncertainty styling, gate evidence drill-down, and keyboard-operable cockpit tabs.
- Required relation endpoints to match known/T-Box entities and field mappings to target existing model elements or properties; stale query evidence is filtered from cards, reports, snapshots, and autosave.
- Bound requested static RDF validation to the exact RDF inputs packaged in the handoff manifest, including base IRI, so a pass cannot approve a different bundle.
- Bound structured answer provenance to the actual current stage, made revise apply explicit corrections with audit history, and rejected owner-only empty actions and arbitrary event classifications.
- Enforced kind-compatible T-Box traceability, source-schema field existence, and handoff freshness on scope/language changes; confirmed owner-tagged actions remain valid follow-up evidence.
- Required a per-question candidate graph pattern: each high-priority answer-shape element and, for multi-element shapes, an endpoint-compatible relation must be linked to that question.
- Required a justification note for every workflow evidence decision so confirm/reject/revise/resolve history is auditable.
- Rejected disconnected Cartesian query evidence and generated connected openCypher/SPARQL seeds for the complete answer shape instead of truncating after two elements.
- Required sequential arrival at `validation_handoff`, preventing direct evidence injection from bypassing the stage workflow while still leaving force-next transitions explicitly audited.
- Added a Textual terminal cockpit with seven workflow evidence panels, predicate gate drill-down, current-stage answers, sequential/forced advancement, review decisions, static RDF validation, request locking, and one no-retry WebSocket update stream.
- Added repository-hosted Codex and Claude Code marketplaces for the shared `ontoforge-workshop` plugin, including stage Markdown forms and local installation helpers.

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
