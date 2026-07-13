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

- each high-priority question has a candidate graph pattern;
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
- report and workshop ZIP.

Gate to complete:

- workshop outputs reflect the current model state;
- unresolved gaps are explicit;
- next-step owners are recorded where possible;
- the assistant does not claim production readiness unless evidence supports it.

## Suggested Data Model Additions

AI-ODLC needs workflow objects beyond the current graph model.

Suggested first-class objects:

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
Risk
Decision
Gate
~~~

Suggested claim shape:

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

Suggested user story shape:

~~~json
{
  "actor": "Quality manager",
  "goal": "Trace product defect causes faster",
  "decision": "Identify affected supplier lots and production lines",
  "success_metric": "Reduce root-cause analysis time from days to hours",
  "priority": "high"
}
~~~

Suggested data source shape:

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

## Suggested API Additions

The current OntoForge REST API can remain, but AI-ODLC needs workflow-state endpoints.

Possible additions:

~~~text
POST /workflow/start
GET  /workflow/state
POST /workflow/answer
POST /workflow/clarify
POST /workflow/advance
POST /workflow/review
GET  /workflow/next-question
GET  /workflow/gates

POST /claim
POST /story
POST /event
POST /question
POST /data-source
POST /mapping
POST /validation-query
POST /rdf-decision
GET  /coverage
~~~

POST /workflow/answer should be the main AI-driven endpoint. A user answer should cause the AI workflow to:

1. store the answer as one or more claims;
2. extract model candidates;
3. update story, event, and question state;
4. detect ambiguity and contradiction;
5. update data mapping needs;
6. update gate status;
7. produce the next best question;
8. push an updated narration/workflow state to the browser.

## TUI and Browser Workflow Improvements

The current viewer is graph-centered. AI-ODLC needs a workshop cockpit that shows both the conversation flow and the model state.

Suggested panels:

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

The UI should make uncertainty visible. A graph node that is confirmed should not look the same as a node that is assumed or missing data mapping.

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

## Gate Summary

| Gate | Required Evidence |
| --- | --- |
| Inception | actor, decision, goal, scope, success metric |
| Discovery | domain narrative, key terms, scenario claims |
| Event Discovery | events, triggers, state changes, unresolved event semantics |
| Story-to-Question | prioritized competency questions and answer shapes |
| Model Synthesis | candidate T-Box/A-Box connected to questions |
| Data Grounding | source mapping and readiness status |
| Adversarial Review | assumptions, risks, contradictions, gaps |
| Validation and Handoff | verified queries, report, exports, action items |

## Implementation Roadmap

## v2 Implementation Status

The v2 implementation delivers a working AI-ODLC vertical slice: server-side workflow state, deterministic answer processing, workflow REST endpoints, evidence-aware next-question generation, automatic adversarial review generation, workflow state in snapshot/autosave/import/report paths, an interactive browser AI-ODLC cockpit, AI-ODLC report sections, updated Claude/Kiro workshop skill instructions, RDF/SHACL handoff export, and smoke/unit checks.

RDF/SHACL support in v2 is intentionally a handoff layer, not production reasoning. It generates Turtle, JSON-LD, SHACL seed shapes, SPARQL seed queries, and mapping notes. Full SPARQL execution/validation, OWL reasoning, named graph policy, and production-grade SHACL constraint design remain follow-up work.

### Phase 1: Documented Workflow and Agent Skill

- Add this workflow design to the repository.
- Update workshop skill instructions to follow AI-ODLC stages.
- Add explicit claim states and adversarial review rules to the skill.
- Keep implementation read-only except for current graph/report endpoints.

### Phase 2: Workflow State Objects

- Add server-side workflow state.
- Add story, question, claim, event, data source, and mapping objects.
- Autosave workflow state with the existing workshop snapshot.
- Include workflow state in report export.

### Phase 3: Cockpit UI

- Add TUI/browser panels for stage, questions, data mappings, risks, and gates.
- Show confidence and readiness status visually.
- Let the operator submit AI-ODLC answers, advance gates, request the next question, and generate adversarial review from the browser cockpit.
- Link graph elements to their source claims and data mappings.

### Phase 4: Validation Expansion

- Generate query candidates from competency questions.
- Track query readiness and verification evidence.
- Add optional SPARQL seed query candidates.
- Add SHACL seed shape generation for required properties, datatypes, and cardinality notes.
- Execute and validate SPARQL candidates in a future phase.

### Phase 5: Export and Handoff Expansion

- Extend the report with AI-ODLC sections.
- Add RDF/SHACL export artifacts.
- Add RDF decisions, validation query seeds, source mappings, and readiness notes to handoff artifacts.
- Add Neptune RDF handoff notes where applicable.
- Package workflow state, report, graph snapshot, property graph export, and RDF artifacts together.

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
