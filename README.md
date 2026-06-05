# OntoForge — Ontology Discovery Workshop Tool

[English](./README.md) · [한국어](./README.ko.md) · [日本語](./README.ja.md)

A local tool for **building and validating ontologies in real time through conversation** with customers. The agreed-upon ontology can be promoted directly to Amazon Neptune to leverage the configuration, build a data model, and reuse it for future ontology work.

## What it does
1. Structures entities, relationships, and properties from conversation → reflected in real time into **Kùzu (an embedded property graph)**
2. **Visualizes the schema (T-Box) and instances (A-Box) as a live graph** (Cytoscape.js)
3. **Validates customer questions with openCypher** — "so this answer really does come from the graph"
4. Automatically generates ontology documentation (Markdown, Obsidian-compatible)
5. **Neptune export** (openCypher scripts + Bulk Loader CSV)

For detailed design, security constraints, and scope, see [`docs/DESIGN.md`](./docs/DESIGN.md) and
[`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md); for conversation skills, see
[`skills/WORKSHOP_SKILLS.md`](./skills/WORKSHOP_SKILLS.md).

### Workshop operation (M2)
- **Start from scratch**: top-left `⟲ Blank` button → build a new customer conversation from the ground up
- **Edit mode**: click an entity/relationship chip in the sidebar to delete it (related relationships are cascade-deleted). Changes during the conversation — e.g. "what if we add a mock exam?" — are reflected in real time
- **Three deliverables**: `📄 Generate the 3 workshop deliverables` button → generated under `exports/report/`
  1. Workshop summary (entities, relationships, validation queries)
  2. Proposed AWS build architecture (automatic Neptune sizing estimate + data flow + compliance)
  3. Data readiness (classification of available/unavailable data, readiness %)
  4. **Technical meeting handoff** — finalized schema, export-for-loading guidance, data mapping actions, validation points, open issues
  - Formats: Markdown + HTML + PDF (weasyprint) + docx (python-docx)
  - Handoff bundle: `neptune.cypher` + `bulk/*.csv` are generated in the same folder → hand the whole folder to the technical team

### Query execution target
Currently, actual openCypher is executed against **Cytoscape** and the results are visualized. Live remote
Neptune queries are planned for M3 (currently export only).

## Quick start

### Windows (PowerShell)
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="src"; $env:ONTOFORGE_FRESH="1"
uvicorn ontology_workshop.server:app --reload
# Browser: http://localhost:8000
```
> weasyprint can be tricky to install/run on Windows without the GTK runtime.
> In that case, only PDF is automatically skipped (the other 3 formats are generated normally), and you can
> open the HTML report in a browser and use "Print → Save as PDF". The tool guides you through this.

### macOS / Linux
```bash
pip install -r requirements.txt

# Seed demo data + console output
PYTHONPATH=src python src/seed_demo.py

# Workshop server (live visualization + skills panel)
PYTHONPATH=src ONTOFORGE_FRESH=1 uvicorn ontology_workshop.server:app --reload
# In your browser: http://localhost:8000
```

### Conversation skills (M1)
In the left panel, transcribe the customer's answers and run a skill; entities and relationships are automatically
reflected into the graph, visualization, and documentation. There are two extraction paths:
- If the `ANTHROPIC_API_KEY` environment variable is set, extraction uses the **Claude API (Sonnet)**
- Otherwise, it falls back to the **offline rule-based extractor** (for on-site demo stability)

Only enable the external Claude API when you have customer-data, legal, and security approval.
If you lack approval or sensitive information may be involved, do not set `ANTHROPIC_API_KEY`; proceed with the
offline extractor, or use an approved Amazon Bedrock model path in a later implementation phase.

Offline extractor domain coverage: education / media & entertainment / gaming / sports /
manufacturing & high-tech / telco / automotive / enterprise (including conglomerate and affiliate models).
Korean input is normalized to English PascalCase entity names (`학생→Student`, `차량→Vehicle`, etc.).
To add domains, add one line each to `_ENTITY_HINTS` and `_mock_relations` in `src/ontology_workshop/skills.py`.

```bash
export ANTHROPIC_API_KEY=<approved-api-key>   # optional: when using API extraction
```

## Architecture
The canonical architecture diagram is in [`docs/architecture.puml`](./docs/architecture.puml), and the
security design is documented in [`docs/DESIGN.md`](./docs/DESIGN.md) and
[`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md).

```
Conversation (Claude + skills) → Orchestrator (FastAPI) → Kùzu (single source of truth, openCypher)
                                                        ├─ WebSocket → Cytoscape visualization
                                                        ├─ Markdown documentation
                                                        └─ Neptune export
```

## Security configuration
OntoForge is a single-operator, local workshop tool. Apply the settings below when handling customer-sensitive information.

1. Bind the local server to `127.0.0.1` and do not expose it on a shared network. Loopback connections (`localhost`, `127.0.0.1`, `::1`) are allowed without a token by default.
2. The default local run starts without a token.
   ```bash
   PYTHONPATH=src ONTOFORGE_FRESH=1 uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   # Browser: http://localhost:8000
   ```
3. If you must expose it on a shared network or enforce authentication even on localhost, configure a REST/WebSocket access token.
   ```bash
   export ONTOFORGE_TOKEN="$(openssl rand -hex 24)"
   export ONTOFORGE_REQUIRE_TOKEN=1  # set only when enforcing the token even on localhost
   PYTHONPATH=src ONTOFORGE_FRESH=1 uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   # Browser: http://localhost:8000/?token=$ONTOFORGE_TOKEN
   # With curl: -H "X-OntoForge-Token: $ONTOFORGE_TOKEN"
   ```
4. In environments that require TLS, use uvicorn's SSL options.
   ```bash
   uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000 \
     --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```
5. Keep `workshop.kuzu` and `exports/` on an encrypted filesystem such as FileVault/BitLocker/LUKS. Export files are created only under `./exports` and stored with `0600` permissions.
6. Store `ANTHROPIC_API_KEY` only in environment variables or an approved secret manager. Mask customer PII, biometric, and regulated data, or turn off external LLM calls and proceed with the offline extractor.
7. Before loading into Amazon Neptune, apply the IAM, S3, VPC, KMS, and audit-log criteria in [`docs/NEPTUNE_SECURITY.md`](./docs/NEPTUNE_SECURITY.md).

For data classification and retention/deletion criteria, follow [`DATA_CLASSIFICATION.md`](./DATA_CLASSIFICATION.md); for security reporting and scan records, follow [`SECURITY.md`](./SECURITY.md).

## Key constraints
- The internal model is a **single property graph**. T-Box/A-Box are conceptually separated in the UI.
- **OWL reasoning is out of scope** — emulate it with Cypher rules if needed; true reasoning is a separate track.
- Local openCypher → Neptune is **mostly** compatible (not 100%). Loading and tuning happen at the technical meeting stage.
- The workshop runs locally inside the customer's security network. The only external communication is the Claude API call.

## License
This project is provided under the Apache-2.0 license. See [`LICENSE`](./LICENSE) for details.
