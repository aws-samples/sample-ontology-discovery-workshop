# AI-ODLC Workflow Design

AI-ODLC stands for **AI-Driven Ontology Discovery Lifecycle**. It is a proposed workflow extension for OntoForge that turns a one-day ontology discovery workshop into an AI-guided, evidence-driven design process.

The goal is not to finish a production ontology in one day. The goal is to produce a validated candidate ontology, mapped data assumptions, unresolved gaps, and a concrete handoff path for property graph, RDF, SHACL, and Amazon Neptune follow-up work.

## Design Intent

OntoForge already supports live property graph modeling, openCypher validation, browser visualization, report generation, and Neptune export. The next workflow layer should make the AI assistant the active workshop facilitator.

In this model:

- the AI asks the next best question;
- the user answers with domain knowledge, user stories, examples, and data structures;
- the AI extracts claims, model candidates, events, questions, and data mappings;
- the AI challenges ambiguity, missing evidence, contradictions, and over-modeling;
- the user clarifies or corrects;
- OntoForge updates the graph, validation state, workshop feed, and handoff artifacts.

This is inspired by AI-assisted lifecycle workflows such as AI-DLC, but adapted for ontology discovery rather than software or database migration delivery.

## Non-Goals

AI-ODLC should avoid overstating what a one-day workshop can achieve.

It does **not** claim to deliver:

- a final enterprise ontology;
- complete coverage of a customer's domain;
- production-grade RDF/OWL reasoning;
- final data quality validation;
- final ownership agreement across all source systems;
- a ready-to-operate multi-user ontology platform.

It should deliver a disciplined discovery result that is good enough for technical handoff, PoC planning, and the next round of model validation.

## Core Principles

### 1. Domain-Neutral Core

The workflow must not be hard-coded for education or any other single domain. Education, manufacturing, media, games, sports, telecom, automotive, finance, healthcare, public sector, and enterprise domains should all use the same core flow.

The core workflow handles generic concepts:

- actor;
- goal;
- business decision;
- user story;
- domain narrative;
- domain event;
- competency question;
- entity candidate;
- relation candidate;
- property candidate;
- data source;
- field mapping;
- validation query;
- assumption;
- risk;
- action item.

Domain-specific knowledge should be optional guidance, not embedded workflow logic. If domain packs are added later, they should provide hints and examples only.

### 2. User Story and Data Structure Together

The workflow should not model only from user stories, and it should not model only from existing database schemas.

User stories explain what the graph must help decide. Data structures explain what can actually be populated and verified.

The AI should continuously connect:

- user story -> competency question;
- competency question -> graph pattern;
- graph pattern -> entity/relation/event/property candidates;
- model element -> source system/table/file/API/log/event stream;
- source field -> graph property or relation;
- missing mapping -> open action item.

### 3. Claims Are Not Facts

Every user statement should be treated as a claim until it is confirmed or grounded.

Suggested claim states:

- candidate - captured but not reviewed;
- confirmed - accepted by the user or domain expert;
- assumed - useful but not yet proven;
- conflicting - contradicts another claim or model element;
- missing_evidence - needs data or an example;
- requires_data_mapping - cannot be validated without source mapping;
- out_of_scope - intentionally excluded from the one-day scope.

The AI should never silently promote a claim to a final model element without recording its confidence, source, and validation status.

### 4. Adversarial Review Is Mandatory

The AI should not behave like a passive note taker. It should actively challenge:

- ambiguous terms;
- duplicated concepts;
- hidden assumptions;
- unclear ownership;
- missing source data;
- inconsistent events;
- over-modeled entities;
- relations that should be event nodes;
- properties that were modeled as entities;
- business claims with no measurable evidence.

This review should be objective and evidence-based, not confrontational. The purpose is to improve the model before handoff.

### 5. One-Day Scope Control

AI-ODLC is a one-day workshop workflow. It should aggressively limit scope.

Recommended completion target:

- 2-5 priority user stories;
- 3-7 competency questions;
- one candidate T-Box;
- representative A-Box examples where available;
- data mapping for high-priority model elements;
- clear unresolved assumptions and gaps;
- initial openCypher validation;
- RDF/SHACL readiness notes where relevant;
- report and handoff action items.

## One-Day Workshop Agenda

The exact timing can change, but the workflow should remain gate-based.

| Time | Stage | Purpose | Primary Outputs |
| --- | --- | --- | --- |
| 09:30-10:15 | Inception | Frame the business decision and success criteria | scope, actors, goals, decisions |
| 10:15-11:15 | Discovery | Capture domain narrative and workflow examples | activities, objects, systems, claims |
| 11:15-12:15 | Event Discovery | Identify important domain events and state changes | events, commands, policies, transitions |
| 13:15-14:15 | Story-to-Question Mapping | Convert goals into competency questions | prioritized questions, answer shapes |
| 14:15-15:15 | Model Synthesis | Build candidate entities, relations, events, and properties | draft T-Box/A-Box |
| 15:15-16:15 | Data Grounding | Map the model to real data structures | sources, fields, owners, readiness |
| 16:15-17:00 | Adversarial Review | Find ambiguity, contradiction, gaps, and over-modeling | risks, assumptions, action items |
| 17:00-17:30 | Validation and Handoff | Validate questions and package outputs | report, export readiness, next steps |

## AI Interaction Loop

Each user interaction should follow the same loop.

~~~text
AI asks one focused question
-> user answers
-> AI extracts structured claims
-> AI updates model candidates and data mappings
-> AI checks ambiguity, conflicts, and missing evidence
-> AI summarizes what changed
-> AI asks the next focused question
~~~

The assistant should prefer one high-value question at a time. Multiple questions are allowed only when they are tightly related and necessary to unblock the current gate.

## Workflow Stages

### 1. Inception

Purpose: define the business reason for the ontology.

The AI should ask for:

- primary actor or decision maker;
- business goal;
- decision to improve;
- success metric;
- one-day workshop scope;
- sensitive data or regulatory constraints;
- desired outputs: property graph, RDF, SHACL, Neptune export, report, or all of them.

Example prompt:

~~~text
Who needs this graph, what decision will it improve, and how will we know the workshop was useful?
~~~

Gate to advance:

- at least one actor is known;
- at least one decision or user goal is known;
- the one-day scope is explicit;
- unsupported expectations are marked out of scope.

### 2. Discovery

Purpose: capture the domain story without forcing the user into formal modeling terms.

The AI should ask the user to describe a real scenario:

- who participates;
- what happens first, next, and last;
- what objects or records are involved;
- which systems are used;
- what exceptions or edge cases matter;
- what decisions are made from the information.

The AI extracts:

- actors;
- activities;
- business objects;
- systems;
- candidate entities;
- candidate relationships;
- claims;
- unresolved terms.

Gate to advance:

- a domain narrative exists;
- key terms have working definitions or are flagged as ambiguous;
- at least one scenario connects to the inception goal.

### 3. Event Discovery

Purpose: discover domain events and state changes. This borrows the useful part of event storming without requiring a full event-storming workshop.

The AI should ask:

- what important things happen;
- what triggers them;
- what state changes;
- what command or user action caused the event;
- what policy or rule reacts to the event;
- which events are business events versus system/log events.

The AI should detect when a relation should become an event node.

Example:

~~~text
Customer PURCHASED Product
~~~

may be too weak if the domain needs time, payment, channel, quantity, or fulfillment details. It may need:

~~~text
Customer -> PLACED -> Order -> CONTAINS -> Product
Order -> PAID_BY -> Payment
Order -> FULFILLED_BY -> Shipment
~~~

Gate to advance:

- important state-changing events are captured;
- event-like concepts are classified as event nodes, relations, or properties;
- unresolved event semantics are listed.

### 4. Story-to-Question Mapping

Purpose: convert user goals into competency questions that can validate the ontology.

The AI should turn each priority user story into questions the graph must answer.

Example structure:

~~~json
{
  "user_story": {
    "actor": "Quality manager",
    "goal": "Trace the likely cause of product defects faster",
    "decision": "Identify affected supplier lots and production lines",
    "success_metric": "Reduce root-cause analysis time from days to hours"
  },
  "competency_questions": [
    {
      "question": "Which products are affected by a defective supplier lot?",
      "expected_answer_shape": ["Product", "Component", "Lot", "Supplier"],
      "priority": "high"
    }
  ]
}
~~~

Gate to advance:

- high-priority stories have competency questions;
- each question has an expected answer shape;
- questions are prioritized for the one-day workshop.

### 5. Model Synthesis

Purpose: create the candidate ontology model.

The AI should synthesize:

- entity types;
- relation types;
- event nodes;
- properties;
- primary keys;
- cardinality notes;
- example instances where available;
- openCypher query candidates;
- RDF/SHACL implications when relevant.

The model should remain candidate-level until reviewed.

Gate to advance:

- each high-priority question has its own candidate graph pattern: every expected
  answer-shape element is explicitly linked to that question and a multi-element
  shape has a question-linked relation between linked endpoint candidates;
- each model element is connected to at least one story, event, question, or data source need;
- obvious duplicates and naming conflicts are reviewed.

### 6. Data Grounding

Purpose: connect the candidate model to real data structures.

The user may provide:

- table schemas;
- CSV headers;
- API payload examples;
- event messages;
- log formats;
- data catalog excerpts;
- source system descriptions.

The AI maps:

- source -> entity;
- source field -> property;
- source key -> node identity;
- foreign key or join path -> relation;
- event record -> event node or edge;
- missing source -> action item.

Example:

~~~text
Product.id         <- quality_inspection.product_id
Defect.code        <- quality_inspection.defect_code
Inspection.time    <- quality_inspection.inspection_time
ProductionLine.id  <- quality_inspection.line_id
~~~

Gate to advance:

- high-priority model elements have available, partial, missing, derived, or unknown status;
- available and partial items have source, owner, and freshness notes where possible;
- missing or unknown items have action items.

### 7. Adversarial Review

Purpose: objectively challenge the draft before handoff.

The AI should produce a review covering:

- ambiguous terms;
- unresolved ownership;
- conflicting claims;
- unsupported causal claims;
- missing data;
- over-generalized entities;
- event modeling mistakes;
- privacy or sensitivity risks;
- RDF/SHACL readiness risks;
- Neptune loading and query risks.

The AI should ask the user to accept, reject, or revise the review findings.

Gate to advance:

- major risks are accepted as action items or resolved;
- assumptions are visible in the report;
- no critical contradiction is hidden.

### 8. Validation and Handoff

Purpose: produce artifacts that the customer and technical team can use after the workshop.

Expected outputs:

- workshop summary;
- user story summary;
- competency question list;
- candidate T-Box/A-Box;
- graph visualization snapshot;
- verified openCypher queries;
- optional SPARQL query candidates;
- data mapping table;
- data readiness matrix;
- assumptions and risks;
- action items by owner;
- Neptune export readiness;
- RDF/SHACL readiness notes;
- latest on-demand static validation evidence and freshness, when requested;
- report and workshop ZIP.

Gate to complete:

- workshop outputs reflect the current model state;
- unresolved gaps are explicit;
- next-step owners are recorded where possible;
- the assistant does not claim production readiness unless evidence supports it.

## Implemented Workflow Data Model

AI-ODLC needs workflow objects beyond the current graph model.

Implemented first-class collections and derived objects:

~~~text
WorkshopStage
Claim
UserStory
DomainEvent
CompetencyQuestion
ModelCandidate
DataSource
FieldMapping
Assumption
Contradiction
Risk
Decision
ReviewFinding
ActionItem
ValidationQuery
RDFDecision
Gate
ReviewRun
TransitionHistory
HandoffManifest
~~~

Representative claim shape:

~~~json
{
  "id": "claim-001",
  "text": "Product defects can be traced to supplier lots and production lines.",
  "source": "workshop conversation",
  "status": "assumed",
  "confidence": "medium",
  "model_impact": ["Product", "Defect", "SupplierLot", "ProductionLine"],
  "data_required": ["quality_inspection", "supplier_lot_master", "mes_events"],
  "risks": [
    "Causal relationship between defect and supplier lot may require statistical validation."
  ],
  "validation_questions": [
    "Do inspection records contain both product ID and supplier lot ID?"
  ]
}
~~~

Representative user story shape:

~~~json
{
  "actor": "Quality manager",
  "goal": "Trace product defect causes faster",
  "decision": "Identify affected supplier lots and production lines",
  "success_metric": "Reduce root-cause analysis time from days to hours",
  "scope": "One traceability scenario in the one-day workshop",
  "priority": "high"
}
~~~

Representative data source shape:

~~~json
{
  "name": "quality_inspection",
  "type": "table",
  "fields": {
    "product_id": "STRING",
    "defect_code": "STRING",
    "inspection_time": "TIMESTAMP",
    "line_id": "STRING"
  },
  "owner": "quality_team",
  "freshness": "daily",
  "sensitivity": "confidential"
}
~~~

## Implemented Workflow API

The v2 server exposes these workflow-state endpoints:

~~~text
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

POST /claim
POST /story
POST /event
POST /question
POST /data-source
POST /mapping
POST /validation-query
POST /rdf-decision
POST /assumption
POST /contradiction
POST /finding
POST /risk
POST /action
GET  /coverage
~~~

`POST /workflow/answer` records evidence only for `current_stage`; a client cannot
change the stage by labeling an answer. `POST /workflow/advance` permits only the
immediate next stage. A forced advance uses the same sequential transition, requires
an explanatory reason, and records the reason, actor, and bypassed gates in workflow
history and the audit log. Skips and backward transitions are rejected.

Structured objects supplied with an answer may populate multiple evidence collections,
but their capture `stage` is always overwritten with the actual current stage. A client
cannot forge future-stage provenance through the extracted payload.

Review decisions use `confirm`, `accept`, `reject`, `revise`, `resolve`, or `start`.
`revise` applies explicitly supplied field corrections and leaves the object in
`revision_requested`; every decision requires a justification note, with classification
or evidence-link changes recorded explicitly in that note.
High-severity risks or findings may be accepted only with a linked action containing
an owner. `update` and `merge` preserve before/after history. Deduplication fills only
empty fields; competing non-empty values become visible `merge_conflicts` until an
explicit update or merge decision resolves them.

`POST /workflow/answer` is the main AI-driven endpoint. A user answer causes the workflow to:

1. store the answer as one or more claims;
2. extract model candidates;
3. update story, event, and question state;
4. detect ambiguity and contradiction;
5. update data mapping needs;
6. update gate status;
7. produce the next best question;
8. push an updated narration/workflow state to the browser.

## Browser and Terminal Cockpits

OntoForge v2 provides both a responsive browser cockpit and a Textual terminal
cockpit. Both consume the same server-owned workflow state; neither duplicates gate
logic. The browser adds the Cytoscape model view, while the terminal surface prioritizes
keyboard operation, predicate evidence, and facilitator actions.

Implemented panel information architecture:

~~~text
[Stage]
- current stage
- completion percentage
- active gate
- next question

[Stories]
- actors
- goals
- decisions
- success metrics

[Events]
- domain events
- commands
- policies
- state changes

[Questions]
- competency questions
- priority
- query readiness

[Model]
- entities
- relations
- event nodes
- properties
- graph diff

[Data]
- sources
- field mappings
- owner
- freshness
- sensitivity
- readiness status

[Review]
- assumptions
- contradictions
- missing evidence
- risks
- action items

[Exports]
- report
- snapshot
- Neptune
- RDF
- SHACL
~~~

The implemented cockpit separates Stories, Events, Questions, Model, Data, Review,
and Actions. Each gate exposes its individual predicates and missing evidence. Review
cards support confirm/accept/reject/revise/resolve decisions, validation cards expose
check-level results and report links, and forced advance requires a reason dialog.
Graph elements and evidence cards visually distinguish confirmed, assumed/candidate,
conflicting, and missing-evidence states. Narrow-screen layouts stack the feed, graph,
and cockpit; keyboard focus, labels, live status announcements, request locking, and
request error handling are included.

Start the optional terminal cockpit after the FastAPI server:

~~~bash
PYTHONPATH=src python -m ontology_workshop.tui --url http://127.0.0.1:8000
~~~

It exposes Stories, Events, Questions, Model, Data, Review, and Actions; current-stage
answers; adjacent-stage advance; audited force-next; bounded adversarial review;
explicit evidence decisions; validation/handoff evidence; and one user-triggered
static RDF handoff check. It consumes one WebSocket update stream and offers manual
Refresh. A closed stream is reported rather than silently reconnected; there is no
polling or automatic review/validation retry.

## RDF and SHACL Readiness

RDF support should not be treated only as a final export format. AI-ODLC should collect RDF-relevant decisions during the workflow.

The AI should ask for or infer, then confirm:

- base namespace;
- class versus individual decisions;
- URI generation rules;
- label language behavior;
- object property versus datatype property;
- event node modeling;
- domain/range implications;
- cardinality and required-field constraints;
- SHACL shapes for validation;
- named graph strategy if needed.

Recommended RDF artifacts:

~~~text
ontology.ttl
instances.ttl
ontology.jsonld
shapes.ttl
queries.sparql
rdf_mapping.md
~~~

Property graph export should remain supported. The workflow should produce both property graph and RDF handoff notes when required.

### Bounded On-demand Validation Loop

The validation loop is deliberately user-triggered and single-run. In the cockpit or through `POST /workflow/validate`, OntoForge generates the current RDF handoff bundle, checks required artifacts, JSON-LD structure, read-only SPARQL seed syntax, and SHACL/T-Box structural coverage, then stores only the latest result as workflow evidence. Source and bundle fingerprints mark that result `stale` if relevant model or workflow inputs later change; this is an on-read comparison, not background monitoring.

A failed run produces at most one deduplicated review finding and one action item. The operator fixes the model or decision, then chooses whether to rerun once; only a `pass` rerun resolves those generated items, while `warning` leaves them open. This keeps the loop useful without turning the AI assistant into a babysitter. No scheduler, polling, background worker, continuous monitoring, or automatic retry is part of this workflow.

The scope is `static_handoff_validation`. It does not execute SPARQL, run a SHACL engine, establish data conformance, perform OWL reasoning, or validate production Neptune performance. Those remain explicit technical handoff tasks.

## Gate Summary

| Gate | Required Evidence |
| --- | --- |
| Inception | high-priority story with actor, goal, decision, success metric, and explicit one-day scope |
| Discovery | discovery narrative linked to a priority story; confirmed terms or a resolved ambiguity decision |
| Event Discovery | event name, trigger, state change, and node/relation/property classification, or explicit no-event rationale; no open event-semantic finding |
| Story-to-Question | every high-priority story covered by prioritized questions with expected answer shapes |
| Model Synthesis | non-empty entity/relation T-Box; every T-Box/candidate traceable to story, event, question, or source with a kind-compatible candidate; relation endpoints match known entities and the T-Box; every high-priority question has linked candidates for all answer-shape elements and, for a multi-element shape, a linked relation pattern; naming conflicts resolved |
| Data Grounding | concrete source-field-target mappings whose fields exist when a source schema is supplied and whose targets are existing model elements/properties, readiness status, source owner/freshness, priority model coverage, and linked actions for missing/unknown mappings |
| Adversarial Review | current bounded review over material evidence covering ambiguity, contradiction, causality, event modeling, over-modeling, and sensitivity; critical items resolved/rejected; high items resolved/rejected or accepted with owned actions |
| Validation and Handoff | canonical adjacent-stage transition history through the final stage, including audited reasons for any forced next step; every preceding gate passed; non-empty current T-Box; exact current-model openCypher seed evidence for every high-priority question; owner-tagged action; current report/snapshot/Neptune/RDF artifact manifest; current PASS static RDF validation if requested; no open validation action |

The final gate does not use a global successful-query count. An ad-hoc query such as
`RETURN 1` cannot verify a competency question: both the question and normalized
openCypher text must match the stored seed, and execution evidence must match the
current query-evidence fingerprint. The query must return MATCH-bound variables for
every expected answer-shape label in one connected relationship pattern; using those
labels only in comments, strings, aliases, or disconnected Cartesian matches does not
establish relevance. Generated openCypher and SPARQL seeds include every answer-shape
element rather than silently truncating shapes longer than two. Query evidence, RDF static validation, and final
handoff packages use separate fingerprints so their freshness cannot substitute for
one another. Static RDF validation remains optional
unless requested, but once requested only a fresh `pass` qualifies. `warning`, stale,
or empty-model results do not qualify. A static pass still does not mean SPARQL was
executed or a SHACL engine established conformance.

When validation was requested, its RDF input fingerprint must also equal the RDF input
fingerprint recorded in the final handoff manifest. A pass generated with one base IRI
cannot approve a package later generated with another base IRI or another RDF input set.

The final completion gate also requires a generated handoff manifest containing
non-empty Markdown/HTML reports, read-only HTML/JSON snapshots, Neptune openCypher and
Bulk Loader files, and RDF ontology/instances/JSON-LD/SHACL/SPARQL/mapping/handoff
files. The manifest is marked complete only when every required artifact was actually
recorded, and stores both the packaged RDF-input fingerprint and a broader handoff
source fingerprint; later graph, workflow,
review-decision, or validation changes mark it stale until the operator regenerates
the report package. Missing or empty recorded files also close the gate. The generated
workshop ZIP is recorded. Artifact generation is user-triggered and is never scheduled or
retried automatically.

## v2 Implementation Status

The v2 implementation delivers a guarded AI-ODLC vertical slice: sequential workflow
state transitions, executable evidence-quality gates, deterministic answer processing,
review-object decision history, semantic adversarial checks, exact competency-query
verification, workflow state in snapshot/autosave/import/report paths, a responsive
browser cockpit, RDF/SHACL handoff export, and an on-demand bounded static validation
loop, plus a Textual terminal cockpit backed by the same REST/WebSocket contracts.

RDF/SHACL support in v2 is intentionally a handoff layer, not production reasoning. It generates Turtle, JSON-LD, SHACL seed shapes, SPARQL seed queries, mapping notes, Neptune RDF follow-up notes, and optional static validation reports. Full SPARQL execution, SHACL engine conformance, OWL reasoning, named graph policy, and production-grade SHACL constraint design remain follow-up work.

Implemented scope includes workflow state and autosave, explicit decision history,
quality gates, browser and terminal cockpit panels, query candidates and verification evidence,
RDF/SHACL/SPARQL seed generation, bounded static validation, AI-ODLC report sections,
Neptune and RDF handoff notes, and a current artifact manifest/ZIP.

Explicit follow-up scope remains standards-complete RDF parsing, live SPARQL execution,
SHACL engine conformance, OWL reasoning, named-graph policy, production Neptune loading
and performance validation, and production-grade SHACL policy design. These are not
silently approximated by the one-day workflow.

## Success Criteria

AI-ODLC is successful if a one-day workshop produces:

- clear business motivation;
- scoped domain narrative;
- prioritized user stories and competency questions;
- candidate ontology model;
- visible assumptions and risks;
- source data mapping;
- verified or ready-to-verify graph questions;
- concrete data gaps and action items;
- handoff artifacts that technical teams can continue from.

The workflow fails if it produces a polished-looking ontology without evidence, data grounding, or explicit uncertainty.
