# Workshop Skill Specification

The conversation layer receives customer answers, runs the skills below in stages, and applies each JSON result to OntoForge through REST endpoints. Each skill returns **JSON only**: no preamble, no Markdown.

AI-ODLC v2 is the top-level workshop lifecycle. The skill outputs below still help populate the graph, but every customer answer should also be recorded as workflow evidence so the cockpit, report, snapshot, RDF handoff, and gate checks stay aligned.

## Language Rule

This specification is written in English. Runtime output follows the selected workshop language:

- detect the user's language from operator/customer input, or ask once if unclear;
- write generated questions, summaries, labels, `why` explanations, data-status notes, and action items in that language;
- keep graph identifiers in English PascalCase / UPPER_SNAKE_CASE;
- preserve customer-provided domain values unless the operator asks for translation.

## 1. `extract_entities`

Prompt instruction: separate domain concepts (entity types) from candidate instances in the customer answer.

```json
{
  "entity_types": [
    {
      "name": "Student",
      "properties": {
        "name": "STRING",
        "grade": "INT64"
      },
      "primary_key": "name"
    }
  ],
  "instances": [
    {
      "etype": "Student",
      "props": {
        "name": "Kim Min-su",
        "grade": 2
      }
    }
  ]
}
```

Apply through `POST /entity` for each type and `POST /instance` for each instance.
Also add candidate model evidence through `POST /model-candidate` or include structured objects in `POST /workflow/answer` when the entity was inferred from conversation rather than confirmed.

## 2. `define_relations`

```json
{
  "relations": [
    {
      "name": "COMPLETED",
      "src": "Student",
      "dst": "Curriculum",
      "cardinality": "N:M",
      "properties": {
        "score": "INT64"
      }
    }
  ],
  "edges": [
    {
      "rtype": "COMPLETED",
      "src_key": "Kim Min-su",
      "dst_key": "Functions",
      "props": {
        "score": 68
      }
    }
  ]
}
```

Apply through `POST /relation` and `POST /edge`.

## 3. `model_properties`

Extract properties and event-like entities, such as exams, purchases, sessions, or incidents. Output uses the same entity/relation/instance/edge shapes as `extract_entities` and `define_relations`.

## 4. `analyze_gaps`

Input: customer question list plus current T-Box from `GET /snapshot`.

```json
{
  "missing_entities": ["Attendance"],
  "missing_relations": [
    {
      "name": "REQUESTED_RELEARN",
      "src": "Teacher",
      "dst": "Curriculum"
    }
  ],
  "rationale": "The relearning-request question needs a relation from Teacher to Curriculum."
}
```

Confirm with the operator, then apply the missing structure through skills 1 and 2.

## 5. `verify_query`

Input: natural-language question. Output: openCypher.

```json
{
  "question": "Which students have low scores and teacher feedback?",
  "cypher": "MATCH (s:Student)-[c:COMPLETED]->(cur:Curriculum) WHERE c.score < 70 MATCH (t:Teacher)-[f:FEEDBACK]->(s) RETURN s.name, cur.title, c.score, f.note"
}
```

Apply through `POST /query`. Include the original `question` to receive evidence text. When the query matches a workflow validation query seed, OntoForge records verification evidence and updates query readiness.

## 6. `map_data_sources`

Input: confirmed T-Box. Output: data availability and source mapping.

```json
{
  "available": [
    {
      "entity": "Student",
      "source": "Student information system",
      "schema": "students(id,name,grade)"
    }
  ],
  "to_be_sourced": [
    {
      "entity": "MockExam",
      "note": "Mock exam results need a separate collection path."
    }
  ]
}
```

Include this in the handoff Markdown/report.
Map concrete sources through `POST /data-source` and `POST /mapping`. Missing, unknown, and partial mappings should become action items or risks during adversarial review.

## 7. AI-ODLC Workflow Evidence

Use these endpoints during the workshop loop:

```text
POST /workflow/start
GET  /workflow/state
POST /workflow/answer
POST /workflow/clarify
POST /workflow/advance
POST /workflow/review
POST /workflow/validate
GET  /workflow/next-question
GET  /workflow/gates
GET  /workflow/items/{collection}
POST /workflow/items/{collection}/{item_id}/decision
GET  /coverage

POST /claim
POST /story
POST /event
POST /question
POST /model-candidate
POST /data-source
POST /mapping
POST /validation-query
POST /rdf-decision
POST /assumption
POST /contradiction
POST /finding
POST /risk
POST /action
```

`POST /workflow/answer` accepts natural language or JSON only for the current stage.
It stores the answer as a claim, extracts conservative workflow objects, updates gates,
generates validation query seeds when enough model context exists, and pushes workflow
state to browser and terminal clients. Do not label an answer with a different stage: advance through
`POST /workflow/advance` first. Advancement permits only the immediate next stage.
Forced advancement requires a meaningful `reason`; never invent one for the operator.

The optional Textual client is a thin API surface, not a second workflow engine:
`PYTHONPATH=src python -m ontology_workshop.tui --url http://127.0.0.1:8000`.
It uses one WebSocket connection plus explicit Refresh and must not add polling,
automatic reconnection, review reruns, or validation retries.

Treat extracted objects as candidate evidence until the operator/customer confirms
them. Use the item decision endpoint for confirm, accept, reject, revise, resolve, or
start, and retain a meaningful decision note for every action. Accepting a high-severity
review item requires a linked action with an owner.
Use explicit update/merge decisions for competing non-empty values; do not overwrite
or hide `merge_conflicts`.

At Model Synthesis, link each answer-shape model candidate to the high-priority
competency question it serves via `question_id` or `question_ids`. If a question has
two or more answer-shape elements, also link a relation candidate whose source and
target are linked entity candidates for that question. A global pool of matching model
names is not a question-specific graph pattern and must not be treated as gate evidence.

Recommended answer payload shape:

```json
{
  "stage": "inception",
  "role": "customer",
  "text": "{\"user_story\":{\"actor\":\"Quality manager\",\"goal\":\"Trace defects faster\",\"decision\":\"Identify affected lots\",\"success_metric\":\"Reduce RCA time\",\"scope\":\"One traceability scenario in the one-day workshop\"}}"
}
```

Run `/workflow/review` once after material story, event, model, and data evidence
exists. The bounded review checks ambiguity, contradictions, unsupported causality,
event-vs-edge choices, duplicate/over-modeled concepts, and sensitive-data handling.
It becomes stale when material evidence or graph structure changes. Do not treat an
auto-generated finding as user acceptance or rerun the review automatically.

For handoff, execute the exact openCypher seed linked to every high-priority competency
question. It must return MATCH-bound variables for the complete expected answer shape
in one connected relationship pattern; aliases, comments, strings, disconnected
Cartesian matches, or `RETURN 1` do not establish relevance. Rerun it after relevant
query/model/data changes make its query-evidence fingerprint stale. That fingerprint is
separate from RDF-validation and handoff-package fingerprints. An arbitrary successful
query does not count. Static RDF validation is a
separate structural check: `warning`, stale, and empty-model results do not qualify as
handoff approval, and even `pass` does not mean SPARQL execution or SHACL conformance.

## 8. RDF and Neptune RDF Handoff

The RDF path is a handoff layer, not production reasoning. Use `POST /export/rdf` or report export to create:

- `ontology.ttl`
- `instances.ttl`
- `ontology.jsonld`
- `shapes.ttl`
- `queries.sparql`
- `rdf_mapping.md`
- `neptune_rdf_handoff.md`
- `validation_report.json` and `validation_report.md` after an on-demand validation run

Capture RDF decisions through `/rdf-decision`: base IRI, URI generation, class-vs-individual choices, label language, object/datatype property decisions, event node strategy, cardinality/required fields, and named graph strategy if needed.

Run `POST /workflow/validate` only when the operator explicitly asks for a handoff check or at the Validation and Handoff stage. It performs one static artifact/SPARQL/SHACL structure check and retains only the latest result. If relevant inputs change afterward, report the result as `stale`; do not rerun it without the operator's choice. Do not poll, schedule, retry automatically, or claim that SPARQL was executed or a SHACL engine established conformance. If it fails, summarize the bounded finding and ask the operator to correct the evidence before choosing whether to rerun once.

## Evolution Loop

When the T-Box changes during conversation, rerun skills 1 and 2 so the graph, documentation, visualization, AI-ODLC workflow evidence, Neptune export, and RDF handoff stay synchronized.
