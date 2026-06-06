# OntoForge — Ontology Discovery Workshop Tool

[English](./README.md) | [Korean](./README.ko.md) | [Japanese](./README.ja.md)

OntoForge is a local workshop tool for building and validating an ontology while talking with a customer. The agreed ontology can later be promoted to Amazon Neptune as the basis for a production graph data model.

## Demo

![OntoForge demo](./images/demo.gif)

## What It Does

1. Extracts entities, relations, and properties from workshop conversation and writes them to **Kuzu**, an embedded property graph database.
2. Visualizes schema (**T-Box**) and instances (**A-Box**) as a live Cytoscape.js graph.
3. Validates customer questions with **openCypher** so participants can see that the graph can answer real business questions.
4. Generates ontology documentation in Markdown.
5. Exports Amazon Neptune-ready artifacts: openCypher scripts and Bulk Loader CSV files.

See [`docs/DESIGN.md`](./docs/DESIGN.md), [`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md), and [`skills/WORKSHOP_SKILLS.md`](./skills/WORKSHOP_SKILLS.md) for design, security, and workshop skill details.

## Language Behavior

Repository documentation and agent skill files are written in English. During a workshop, the agent should detect the user's language from the operator/customer input and use that language for:

- direct replies to the user,
- browser feed messages sent through `/narrate`,
- human-readable `title` / `name` labels on graph instances,
- report `descriptions`, `data_status` notes, and `action_items`,
- the `/export/report` `lang` field when the language is supported (`ko`, `en`, `ja`).

Graph identifiers remain standardized in English regardless of workshop language: entity types use PascalCase, relation types use UPPER_SNAKE_CASE, and properties use Kuzu-compatible names and types. If the language is ambiguous, ask once at the start of the workshop. If the user changes language later, switch the workshop responses and generated human-readable text to the new language.

## Workshop Operation

- **Fresh start**: use the reset control in the UI or call `POST /reset`.
- **Change mode**: click entity/relation chips in the sidebar to remove them. Related relation types are removed when an entity type is dropped.
- **Deliverables**: generate report, snapshot, and Neptune export artifacts under `exports/`.
  1. Workshop summary: entities, relations, and verified questions.
  2. AWS architecture recommendation: Amazon Neptune sizing, data flow, compliance, and security controls.
  3. Data readiness status: available, partially available, missing, derived, or unknown.
  4. Technical handoff: confirmed schema, export guidance, mapping actions, validation points, and open issues.
  5. Formats: Markdown, HTML, PDF when WeasyPrint is available, and DOCX.

## Query Target

The local workshop runs openCypher against the embedded Kuzu graph and visualizes the result in Cytoscape. Live remote Amazon Neptune queries are out of scope for this sample; the current Neptune path is export only.

## Quick Start

### Windows (PowerShell)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="src"
uvicorn ontology_workshop.server:app --reload
# Browser: http://localhost:8000
```

If WeasyPrint cannot run because GTK runtime libraries are missing, PDF generation is skipped and the other report formats still work. Use the HTML report and the browser's print-to-PDF flow if needed.

### macOS / Linux

```bash
pip install -r requirements.txt

# Seed demo data and print console output.
PYTHONPATH=src python src/seed_demo.py

# Workshop server with live visualization and skill panel.
PYTHONPATH=src uvicorn ontology_workshop.server:app --reload
# Browser: http://localhost:8000
```

## Persistence and Restore

Workshop data is persisted in `workshop.kuzu` by default. Restart the server without `ONTOFORGE_FRESH=1` to continue the existing workshop:

```bash
PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
```

On a normal restart, OntoForge reloads:

- graph schema and instance data from `workshop.kuzu`;
- workshop feed and verified queries from `exports/session/workshop_snapshot.json`;
- the latest graph state from the autosave snapshot if the Kuzu graph is empty.

OntoForge writes the autosave snapshot after graph, narration, query, import, reset, or report changes. This means a workshop can usually be recovered by starting the server again with the normal command above.

Use `ONTOFORGE_FRESH=1` only when you explicitly want to delete the local Kuzu database at startup. If a fresh start was used accidentally and the autosave file still exists, restart without `ONTOFORGE_FRESH=1`; the server can rebuild the graph from `exports/session/workshop_snapshot.json`.

If you intentionally want a blank workshop, start the server normally and then use the UI reset button or call:

```bash
curl -X POST http://localhost:8000/reset
```

## Conversation Skill

The agent, not the browser UI, is the source of truth for workshop extraction. When the operator provides customer answers, the agent should structure them into entity types, relation types, instances, edges, queries, and report descriptions, then apply them through the REST API.

The browser panel also contains a lightweight extraction path for demos:

- If `ANTHROPIC_API_KEY` is set, the browser-side skill endpoint can call Claude API for extraction.
- If the key is not set, it falls back to an offline rule-based extractor.

Enable external Claude API use only when customer data handling, legal, and security approval exists. If approval is missing or sensitive data may be present, do not set `ANTHROPIC_API_KEY`; use offline extraction or a future approved Amazon Bedrock path.

```bash
export ANTHROPIC_API_KEY=<approved-api-key>   # Optional: API extraction only.
```

## Architecture

The formal architecture diagram is in [`docs/architecture.puml`](./docs/architecture.puml). Security design is documented in [`docs/DESIGN.md`](./docs/DESIGN.md) and [`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md).

```text
Conversation agent -> FastAPI orchestrator -> Kuzu (single source of truth, openCypher)
                                           |-> WebSocket -> Cytoscape visualization
                                           |-> Markdown documentation
                                           |-> Amazon Neptune export
```

## Security Configuration

OntoForge is designed as a single-operator local workshop tool. Apply the controls below when customer-sensitive data may be handled.

1. Bind the local server to `127.0.0.1` and do not expose it to a shared network. Loopback access (`localhost`, `127.0.0.1`, `::1`) is allowed without a token by default.
2. Start normal local workshops without a token.
   ```bash
   PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   # Browser: http://localhost:8000
   ```
3. If the server is exposed to a shared network, or if localhost must also be token-gated, set a REST/WebSocket access token.
   ```bash
   export ONTOFORGE_TOKEN="$(openssl rand -hex 24)"
   export ONTOFORGE_REQUIRE_TOKEN=1  # Only when localhost must require the token.
   PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   # Browser: http://localhost:8000/?token=$ONTOFORGE_TOKEN
   # curl: -H "X-OntoForge-Token: $ONTOFORGE_TOKEN"
   ```
4. Use uvicorn TLS options when TLS is required.
   ```bash
   uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000 \
     --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```
5. Store `workshop.kuzu` and `exports/` on an encrypted filesystem such as FileVault, BitLocker, or LUKS. Export files are constrained to `./exports` and written with `0600` permissions.
6. Store `ANTHROPIC_API_KEY` only in environment variables or an approved secret manager. Mask personal, biometric, regulated, or otherwise sensitive customer data before any external LLM call.
7. Before loading data into Amazon Neptune, apply the IAM, S3, VPC, KMS, and audit logging guidance in [`docs/NEPTUNE_SECURITY.md`](./docs/NEPTUNE_SECURITY.md).

Data classification and retention rules are in [`DATA_CLASSIFICATION.md`](./DATA_CLASSIFICATION.md). Security reporting and scan records are in [`SECURITY.md`](./SECURITY.md).

## Constraints

- The internal model is a single property graph. T-Box and A-Box are conceptual UI/documentation views.
- OWL reasoning is out of scope. Use Cypher rules for lightweight workshop checks; use a separate track for formal reasoning.
- Local openCypher is mostly compatible with Amazon Neptune openCypher, but not guaranteed to be 100% identical. Production loading and tuning belong in the technical handoff phase.
- The workshop is intended to run locally inside the customer's controlled environment. External communication should be disabled unless explicitly approved.

## License

This project is licensed under Apache-2.0. See [`LICENSE`](./LICENSE) for details.
