---
name: ontoforge-workshop
description: Run a customer discovery workshop as a live ontology. Use the OntoForge web viewer, structure operator-provided customer answers into entity types, relation types, properties, instances, and openCypher queries, then apply them to the local graph through REST. Conversation happens in the agent session; the browser renders the graph. Trigger on "ontology workshop", "OntoForge", "start workshop", T-Box/A-Box modeling, live graph validation, report export, or snapshot restore.
copyright: Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
license: Apache-2.0
---

# OntoForge Workshop Operation Skill

## Your Role

You are the workshop brain. The web app is the viewer and local orchestrator; it does not own the workshop reasoning. When the operator gives you customer answers, you extract entity types, relation types, properties, instances, edges, and openCypher queries yourself, then apply them to the local OntoForge server through REST. The browser receives updates through WebSocket and renders the live graph.

- Conversation = this agent session.
- Graph and timeline = browser at `http://localhost:8000`.
- Do not rely on the browser's offline mock extractor as the workshop source of truth.
- AI-extracted entities, relations, and queries are candidates until reviewed by the customer domain expert.
- Mask customer personal or sensitive data before input and confirm data classification, retention, and deletion rules before export.

## Language Rule

The skill file is written in English, but runtime communication follows the user.

- Detect the user's language from the operator/customer input at the start of the workshop. If it is unclear, ask once.
- Use the selected language for direct replies, `/narrate` titles/text, report `descriptions`, `data_status` notes, and `action_items`.
- Pass `"lang":"ko|en|ja"` to `/export/report` when the selected language is supported. If the language is unsupported by the report template, use English for the template and the user's language for free-text descriptions when practical.
- Keep graph identifiers in English: entity type names use PascalCase, relation type names use UPPER_SNAKE_CASE, and properties use Kuzu-compatible identifiers.
- Do not translate customer-provided domain data unless the operator asks. Human-readable `title` or `name` labels should be in the selected workshop language when you create them.
- If the user changes language during the workshop, switch direct replies and newly generated human-readable text to that language.

## Conversation Style

- No filler, greetings, self-introductions, or praise.
- Each turn should contain only two things: one-line summary of what was reflected, then one question for the next required input.
- Ask only questions that advance the current stage or gate.
- Do not fill unknowns by guessing. Standardize names and types yourself, but ask for missing business facts.
- Mirror operator/customer utterances to `/narrate` when the screen timeline should preserve them.

## 0. Setup

Project path: `$PROJECT_ROOT` (example: `/path/to/ontology-workshop`)

Check whether the server is running; start it if needed:

```bash
cd "${PROJECT_ROOT:-/path/to/ontology-workshop}"
curl -s http://localhost:8000/snapshot >/dev/null 2>&1 || \
  (PYTHONPATH=src .venv/bin/uvicorn ontology_workshop.server:app \
   --host 127.0.0.1 --port 8000 > /tmp/ontoforge.log 2>&1 &)
```

Do not set `ONTOFORGE_FRESH=1` for normal restarts; it deletes the local Kuzu database before startup. A normal restart reloads graph schema and instances from `workshop.kuzu`, reloads feed/query state from `exports/session/workshop_snapshot.json`, and can rebuild the graph from that autosave if Kuzu is empty.

When ready, tell the operator to open `http://localhost:8000`. For a new customer, reset the graph explicitly with:

```bash
curl -X POST http://localhost:8000/reset
```

Use `BASE=http://localhost:8000` for REST calls.

## 1. Workshop Loop

For each customer answer provided by the operator:

1. Record the answer as workflow evidence through `/workflow/answer` or `/claim`.
2. Extract the structure needed for the current AI-ODLC stage.
3. Apply workflow objects through `/story`, `/event`, `/question`, `/model-candidate`, `/data-source`, `/mapping`, or `/workflow/review`.
4. Apply graph objects through `/entity`, `/relation`, `/instance`, `/edge`, and `/query`.
5. Push a human-readable summary to `/narrate`.
6. Check `/coverage` or `/workflow/gates`.
7. Give the operator a short spoken/text summary and ask the next single question.

Use `kind:"chat"` in `/narrate` if the conversation itself should appear in the browser timeline.

## 2. Standardization Rules

- Entity type names: English PascalCase, such as `Student`, `Subscriber`, `Vehicle`.
- Relation type names: English UPPER_SNAKE_CASE verb phrases, such as `COMPLETED`, `VIEWED`, `SUBSCRIBES_TO`.
- Property and primary key types: Kuzu types only: `STRING | INT64 | DOUBLE | BOOLEAN | DATE | TIMESTAMP`.
- Human-readable labels are required. Every entity instance should have a `title` or `name` string in the workshop language when practical. The viewer chooses `title` -> `name` -> primary key as the node label.
- Values such as score, status, completion flag, confidence, or timestamp should usually be edge properties rather than separate nodes.
- Use Kuzu/Amazon Neptune-compatible openCypher.

## 3. REST Cheat Sheet

All requests use `Content-Type: application/json`.

### AI-ODLC Workflow State

Use these endpoints to make the AI-driven workshop state first-class. The browser AI-ODLC panel, autosave snapshot, report, and handoff package use this state.

```bash
curl -s -X POST $BASE/workflow/start -H 'Content-Type: application/json' -d '{
  "language":"ko","scope":"one-day ontology discovery","reset":false}'

curl -s -X POST $BASE/workflow/answer -H 'Content-Type: application/json' -d '{
  "stage":"discovery","text":"The customer scenario or clarification...","status":"candidate"}'

curl -s -X POST $BASE/story -H 'Content-Type: application/json' -d '{
  "actor":"Quality manager","goal":"Trace defects faster",
  "decision":"Identify affected supplier lots","success_metric":"Reduce RCA time",
  "priority":"high"}'

curl -s -X POST $BASE/event -H 'Content-Type: application/json' -d '{
  "name":"DefectDetected","trigger":"Inspection result",
  "state_change":"Product enters investigation"}'

curl -s -X POST $BASE/question -H 'Content-Type: application/json' -d '{
  "question":"Which supplier lots are connected to defective products?",
  "expected_answer_shape":["Product","SupplierLot"],"priority":"high"}'

curl -s -X POST $BASE/model-candidate -H 'Content-Type: application/json' -d '{
  "kind":"entity","name":"Product","rationale":"Anchors defect traceability."}'

curl -s -X POST $BASE/data-source -H 'Content-Type: application/json' -d '{
  "name":"quality_inspection","type":"table","owner":"quality_team","freshness":"daily"}'

curl -s -X POST $BASE/mapping -H 'Content-Type: application/json' -d '{
  "source":"quality_inspection","source_field":"product_id",
  "target":"Product.id","status":"available"}'

curl -s -X POST $BASE/validation-query -H 'Content-Type: application/json' -d '{
  "language":"openCypher","question":"Which supplier lots are connected to defective products?",
  "query":"MATCH (p:Product)-[r]-(l:SupplierLot) RETURN p,r,l LIMIT 25",
  "readiness":"ready_to_draft","status":"candidate"}'

curl -s -X POST $BASE/rdf-decision -H 'Content-Type: application/json' -d '{
  "topic":"base_iri","value":"https://example.com/quality/",
  "status":"candidate"}'

# Empty body asks OntoForge to generate an evidence-based adversarial review from current gates.
curl -s -X POST $BASE/workflow/review -H 'Content-Type: application/json' -d '{
  "risks":[{"text":"Supplier lot causality needs validation.","status":"open"}],
  "action_items":[{"text":"Confirm supplier lot keys.","owner":"customer","status":"open"}]}'
```

Read state and gates:

```bash
curl -s $BASE/workflow/state
curl -s $BASE/workflow/next-question
curl -s $BASE/workflow/gates
curl -s $BASE/coverage
```

### Entity Type (T-Box)

```bash
curl -s -X POST $BASE/entity -H 'Content-Type: application/json' -d '{
  "name":"Student","properties":{"name":"STRING","grade":"INT64"},"primary_key":"name"}'
```

### Relation Type (T-Box)

```bash
curl -s -X POST $BASE/relation -H 'Content-Type: application/json' -d '{
  "name":"COMPLETED","src":"Student","dst":"Curriculum","cardinality":"N:M",
  "properties":{"score":"INT64"}}'
```

### Instance Node (A-Box)

```bash
curl -s -X POST $BASE/instance -H 'Content-Type: application/json' -d '{
  "etype":"Student","props":{"name":"Kim Min-su","grade":2}}'
```

### Instance Edge (A-Box)

`src_key` and `dst_key` are the primary key values of each endpoint entity.

```bash
curl -s -X POST $BASE/edge -H 'Content-Type: application/json' -d '{
  "rtype":"COMPLETED","src_key":"Kim Min-su","dst_key":"Quadratic Equations","props":{"score":55}}'
```

### Query Validation

```bash
curl -s -X POST $BASE/query -H 'Content-Type: application/json' -d '{
  "cypher":"MATCH (s:Student)-[c:COMPLETED]->(cur:Curriculum) WHERE c.score<70 RETURN s.name,cur.title,c.score",
  "question":"Which students need remediation?"}'
```

### Focus / Filter

Use focus to project query answers directly on the graph. Node IDs use `{etype}:{pk}`.

```bash
curl -s -X POST $BASE/focus -H 'Content-Type: application/json' -d '{
  "mode":"isolate","label":"Students needing remediation",
  "ids":["Student:Kim Min-su","Student:Park Ji-hun","ExamArea:Algebra"]}'
```

Clear focus:

```bash
curl -s -X POST $BASE/focus -H 'Content-Type: application/json' -d '{"mode":"clear"}'
```

Recommended pattern: run `/query`, then send a `qa` narration with `meta.focus={label, ids}` so the feed card has a "show only this result" action. You may also call `/focus` immediately.

### Browser Feed

```bash
curl -s -X POST $BASE/narrate -H 'Content-Type: application/json' -d '{
  "kind":"reflect","title":"Entity types added","text":"Added Student, Parent, and Teacher."}'
```

### Change / Delete

- `POST /drop {"kind":"entity"|"relation","name":"..."}`
- `POST /instance/delete {"etype":"...","key":"..."}`
- `POST /edge/delete {"rtype":"...","src_key":"...","dst_key":"..."}`
- `POST /reset`

### Export / Deliverables

- `POST /export/neptune` - openCypher script and Bulk Loader CSV files under `exports/`.
- `POST /export/rdf` - Turtle ontology/instances, JSON-LD, SHACL seed shapes, SPARQL seed queries, and RDF mapping notes under `exports/rdf`.
- `POST /export/report {"title":"...","lang":"ko|en|ja","descriptions":{...},"data_status":{...},"action_items":{...}}` - report, handoff, standalone snapshot HTML, and restore JSON.
- `POST /import` - restore a workshop from `workshop_snapshot.json`.
- `GET /files/workshop_report.html`
- `GET /export/snapshot.html`
- `GET /download/workshop.zip`
- `GET /snapshot`
- `GET /markdown`

## 4. `/narrate` Rules

Card kinds:

- `chat` - conversation timeline; use `role: customer|operator|agent`.
- `reflect` - graph update summary.
- `qa` - query Q&A. Include `meta` with `{cypher, count, columns, rows}`.
- `note` / `system` - general notes and system messages.

Every `qa` narration must include:

1. `meta.focus`, even when result count is zero. Include IDs for the answer nodes and any context nodes needed to understand the result.
2. Actionable interpretation in the selected language: what the result reveals, why it matters, and what action should be taken. Include useful numeric evidence in the query output when possible.

Example:

```bash
curl -s -X POST $BASE/narrate -H 'Content-Type: application/json' -d '{
  "kind":"qa","text":"Low-score students - prioritize the largest score gap first.",
  "meta":{"cypher":"MATCH (s:Student)... RETURN s.name, c.score, ...","count":2,
          "columns":["s.name","c.score","f.note"],
          "rows":[["Kim Min-su",55,"Needs remediation"],["Park Ji-hun",45,"Repeat fundamentals"]],
          "focus":{"label":"Students needing remediation","ids":["Student:Kim Min-su","Student:Park Ji-hun"]}}}'
```

## 5. Workshop Stages and Gates

The workshop is gate-based. Do not advance until the current gate is complete.

```text
[A] Modeling -> Gate 1 Query Coverage -> Gate 2 Data Status
             -> Gate 3 Data Location -> [E] Architecture + Migration + Export
```

AI-ODLC v2 is the top-level workshop lifecycle:

```text
Inception -> Discovery -> Event Discovery -> Story-to-Question
          -> Model Synthesis -> Data Grounding -> Adversarial Review
          -> Validation and Handoff
```

Use `/workflow/state`, `/workflow/gates`, and `/coverage` to keep the browser AI-ODLC cockpit and report aligned with the conversation. Do not advance a stage unless the current gate is pass or the operator explicitly accepts the risk.

### AI-ODLC Stage Responsibilities

- Inception: capture actor, goal, decision, success metric, scope, and selected language. Store through `/story` and `/workflow/start`.
- Discovery: capture the domain narrative as claims through `/workflow/answer` or `/claim`; mark uncertainty with `candidate`, `assumed`, `missing_evidence`, `conflicting`, or `out_of_scope`.
- Event Discovery: identify business events, commands, policies, and state changes through `/event`.
- Story-to-Question Mapping: convert user stories into competency questions through `/question`.
- Model Synthesis: create graph model candidates through `/model-candidate`, then apply accepted T-Box/A-Box objects through `/entity`, `/relation`, `/instance`, and `/edge`.
- Data Grounding: map source systems, tables, files, APIs, logs, and event streams through `/data-source` and `/mapping`.
- Adversarial Review: record assumptions, risks, contradictions, missing evidence, and action items through `/workflow/review`.
- Validation and Handoff: run `/query`, narrate evidence as `qa`, verify `/coverage`, then export report/snapshot/Neptune artifacts.

### A. Ontology Modeling

Order: entity types -> relation types -> properties/events -> real instances.

- Entity types (`/entity`): register all core nouns and confirm the list.
- Relation types (`/relation`): define direction and cardinality. Leave zero isolated entity types when possible.
- Properties and events: put values on nodes/edges; model business events as entities only when they have identity or lifecycle.
- Real data (`/instance` + `/edge`): add enough concrete examples to make the graph understandable.

Completion condition: all four categories are represented and the graph is not empty.

### Gate 1 - Query Coverage

Question: can the current structure express and answer every customer question?

- Record the full customer question/use-case list.
- Run each question through `/query`.
- Narrate each passing query as `qa` with `meta.focus`, then project it on the graph.
- If a question cannot be answered, return to modeling, add the missing entity/relation/property/content, and rerun.
- Gate opens only when every customer question is answerable or explicitly documented as out of scope.
- Push a coverage matrix to `/narrate` as a `note`.

### Gate 2 - Data Status

Question: does the data for each entity, relation, and metadata property exist now?

Classify every element as:

- available
- partially available
- missing
- derived
- unknown

Unknown is acceptable when the workshop cannot confirm the answer, especially when customer developers are absent. Unknown, missing, and partial items become customer follow-up actions.

Store the classification for report export:

```json
{
  "Student": {
    "kind": "entity",
    "status": "available",
    "where": "system/table/key",
    "note": ""
  }
}
```

Gate opens only when every element has one classification.

### Gate 3 - Data Location

Question: where is every available or partially available data element, and how will missing elements be created?

For each Gate 2 item, collect source system/table/file, owner, refresh cadence, format, and key fields. For missing items, record an acquisition or generation plan. Gate opens only when all available/partial items have locations and all missing items have a plan.

### E. Architecture, Migration, Synchronization, and Export

Recommend AWS architecture and a phased plan: PoC -> load -> automated enrichment -> operational cutover -> continuous synchronization.

Security baseline:

1. Network: Amazon Neptune in private subnets, only application security groups can reach port 8182, VPC Flow Logs enabled. Target: zero public internet exposure.
2. IAM: query roles scoped to `neptune-db:ReadDataViaQuery` / `WriteDataViaQuery` on target cluster ARNs; Bulk Loader roles scoped to required S3 prefixes only. Target: zero wildcard resources.
3. Encryption: Amazon Neptune storage encryption with AWS KMS, S3 SSE-KMS, S3 Block Public Access, deny insecure transport, TLS 1.2+. Target: 100% encryption in transit and at rest.
4. AI security: for Amazon Bedrock AgentCore or Claude use, validate input length and schema, screen prompt-injection indicators, validate generated openCypher as read-only before execution, and require human review. Target: zero unvalidated query execution.
5. Shared responsibility: AWS secures the cloud infrastructure; the customer/build team secures data classification, IAM, VPC, KMS, application access control, and audit logs.

Integrity baseline:

- Idempotent `MERGE` upsert by primary key.
- No automatic DDL on schema drift without human approval.
- Confirm both endpoint nodes before edge load; orphan edges target: zero.
- Do not overwrite human-reviewed edges (`source=human`) with automated recomputation.
- Stop and roll back on empty labels, isolated required nodes, cardinality violations, or duplicate primary keys.

Export:

- Run `POST /export/report` with localized `descriptions`, `data_status`, and `action_items`.
- Run `POST /export/neptune`.
- Tell the operator where to find report, snapshot, ZIP, and Neptune artifacts.

## 6. Operating Principles

- Keep the rhythm: one customer answer -> reflect to graph -> verify on screen.
- Gates open only when fully satisfied. If a gate is closed, return to the missing stage.
- Prefer one-line confirmation before applying a large extraction.
- Communicate in the selected workshop language. Keep graph identifiers in English.

## 7. Pre-Export Checklist

Before export, report this checklist to the operator and push the same summary to `/narrate`:

1. Stage/gate status: A, Gate 1, Gate 2, Gate 3, E as pass/partial/fail with one-line reason.
2. Customer question coverage matrix: every question, answerable or not, and reason.
3. Unresolved gaps: model gaps, data gaps, and deliverable gaps.
4. Next actions in priority order.

If the checklist has partial/fail items, fix what can be fixed before report generation. Only unresolved items with clear reasons should remain in the final report.

## 8. Report Descriptions

The report is read by non-developers. Auto-generated T-Box/A-Box tables are not enough; you must inject labels and "why this matters" descriptions in the selected workshop language.

Example:

```json
{
  "title": "Customer Knowledge Graph - Ontology Workshop Result",
  "lang": "en",
  "descriptions": {
    "domain": "This graph explains which learning gaps should be remediated first.",
    "entities": {
      "Content": {
        "label": "Content",
        "why": "Content anchors learning progress, weak areas, and recommendations."
      }
    },
    "relations": {
      "WEAK_IN": {
        "label": "Weak in",
        "why": "This relation identifies the exact skill area where intervention is needed."
      }
    }
  }
}
```

Missing labels fall back to the type name; missing `why` text is shown as needing more explanation. Fill both whenever possible.

## 9. Restore From Snapshot

If the operator wants to continue from a previous workshop:

1. Ensure the server is running.
2. Prefer `workshop_snapshot.json` and post it directly to `/import`.
3. If only `workshop_snapshot.html` exists, extract the embedded JSON first.

```bash
curl -s -X POST $BASE/import -H 'Content-Type: application/json' -d @workshop_snapshot.json
```

HTML extraction fallback:

```bash
python3 -c "import re,sys;h=open('workshop_snapshot.html',encoding='utf-8').read();\
m=re.search(r'window.__ONTOFORGE_SNAPSHOT__ = (\{.*?\});',h,re.S);open('/tmp/snap.json','w').write(m.group(1))"
curl -s -X POST $BASE/import -H 'Content-Type: application/json' -d @/tmp/snap.json
```

Report restored counts from the response: entity types, relation types, nodes, edges, narrations, verified queries, and skipped edges. If `skipped_edges > 0`, inspect snapshot consistency.
