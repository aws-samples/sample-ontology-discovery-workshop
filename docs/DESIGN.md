# OntoForge Design and Security Notes

OntoForge is a local-first workshop tool. It turns customer domain discussion into a property graph, guides the session through AI-ODLC workflow evidence, visualizes the result in a browser, and exports agreed artifacts for later Amazon Neptune, RDF, and SHACL follow-up work.

## Architecture

The formal architecture diagram is in [architecture.puml](architecture.puml).

Core components:

* `ontology_workshop.server`: FastAPI REST and WebSocket server.
* `ontology_workshop.graph`: Kuzu-backed property graph store.
* `ontology_workshop.skills`: Claude API or offline-rule extraction.
* `ontology_workshop.workflow`: AI-ODLC stage, claim, story, event, question, data mapping, validation query, RDF decision, risk, and gate state.
* `ontology_workshop.rdf_export`: RDF/JSON-LD/SHACL/SPARQL and Neptune RDF handoff artifact generation.
* `ontology_workshop.rdf_validation`: dependency-free, on-demand structural validation of the RDF handoff bundle.
* `static/index.html`: Cytoscape.js browser viewer using a local vendored script.
* `exports/`: reports, static snapshots, openCypher, Neptune Bulk Loader CSV, RDF handoff bundles, and autosave session snapshots.

## AI-ODLC Workflow Layer

AI-ODLC is the workshop lifecycle layer around the graph. It stores evidence that the graph alone cannot represent safely:

* claims and their status;
* user stories and decisions;
* domain events;
* competency questions and answer shapes;
* model candidates;
* data sources and field mappings;
* validation query seeds and openCypher verification evidence;
* RDF decisions;
* assumptions, contradictions, risks, review findings, action items, and decision history.

`POST /workflow/answer` is the main entry point. It records a claim only against the
current stage, conservatively extracts workflow objects from natural language or JSON,
updates gate coverage, generates the next focused question, and broadcasts the new
workflow state to the browser and terminal cockpits. It cannot change stages. Advancement is
sequential; a forced next-step requires a reason and is retained in workflow history
and the audit log. It does not claim production ontology readiness.

The responsive browser cockpit separates Stories, Events, Questions, Model, Data,
Review, and Actions. It exposes gate predicates, evidence status, explicit review
decisions, validation checks/report links, safe force-advance confirmation, and one
explicit RDF/SHACL static validation run. The Textual terminal cockpit provides the
same seven evidence panels and state-changing controls through the existing REST API;
gate logic remains server-owned. It listens to one WebSocket stream, offers explicit
Refresh, and never polls, reconnects, reruns reviews, or retries validation automatically.

Gate completion is computed from evidence quality and traceability rather than object
counts. High-priority stories require scope and success criteria; questions require
answer shapes and story links; model elements and T-Box types require traceable needs;
candidate kinds must agree with T-Box entity/relation kinds; relation endpoints must
reference known entities and match the T-Box. Global model-name coverage is not enough:
each high-priority question must link every expected answer-shape candidate, and shapes
with two or more elements must also link a relation whose endpoints are linked entities
for that same question. Field mappings must use supplied source
fields and target existing model elements/properties; data gaps require owned actions.
Handoff requires the complete canonical adjacent-stage transition history through
`validation_handoff` (with reasons on forced next steps) and an exact successful openCypher seed
match for every high-priority competency question and the execution fingerprint must
match the current query inputs. The query must return MATCH-bound variables for each
expected answer-shape label in one connected relationship pattern; merely mentioning
labels in aliases, strings, comments, or disconnected Cartesian matches does not
qualify. Seed generation covers the complete answer shape, including shapes longer
than two elements. Query-evidence, RDF static-validation, and final handoff-package
fingerprints are separate trust domains, so freshness cannot leak between them. A
global count of successful or ad-hoc queries is not completion evidence.

Reviewable objects use explicit confirm/accept/reject/revise/resolve transitions with
before/after history and a required decision note. A high-severity item can be accepted only with an owner-tagged
linked action. Conflicting duplicate values are retained as merge proposals rather
than silently overwriting or hiding the existing value. The bounded adversarial review
checks ambiguity, claim contradiction, unsupported causality, event-vs-edge risk,
over-modeling/duplicates, and sensitive-data handling; its result becomes stale when
material evidence or full T-Box structure changes, including property definitions that
do not change entity/relation counts.

Answer extraction always stamps structured objects with the actual current stage;
client-provided future-stage provenance is ignored. `revise` applies explicit field
corrections while retaining `revision_requested`, and review classification/evidence
link edits require a recorded decision note.

`POST /workflow/validate` generates a current RDF bundle and performs one bounded `static_handoff_validation`. It checks required/non-empty files, JSON-LD structure, Turtle prefixes and balanced syntax, T-Box declarations, read-only SPARQL seed structure, and SHACL seed coverage for classes, datatypes, primary keys, and relationships. Only `last_validation` is retained. Source and bundle fingerprints make an older result visibly `stale` after relevant graph/workflow changes. A failed run creates at most one deduplicated finding and action; a passing rerun resolves them. There is no scheduler, polling, background worker, or automatic retry.

If validation was requested, final handoff additionally compares that run's RDF input
fingerprint with the manifest's packaged RDF input fingerprint. Base-IRI or other RDF
input drift therefore requires an explicit new validation; a pass for a different
bundle cannot approve the current package.

A warning-only rerun does not resolve a prior failure action. A repeated adversarial
issue that was previously resolved is reopened as `revision_requested` when it is
detected against changed material evidence.

## Export and Handoff Artifacts

Report export packages the property graph, workflow state, verified openCypher evidence, Neptune openCypher/Bulk Loader files, standalone snapshot, and RDF handoff files. RDF handoff includes `ontology.ttl`, `instances.ttl`, `ontology.jsonld`, `shapes.ttl`, `queries.sparql`, `rdf_mapping.md`, and `neptune_rdf_handoff.md`. When validation has been run, its latest evidence is also rendered as `validation_report.json` and `validation_report.md`.

A successful report export records a handoff manifest only after required report,
snapshot, Neptune, and RDF files exist and are non-empty. Its combined graph/workflow
fingerprint makes that manifest stale after a material change, so the final handoff
gate cannot pass on an older package.

RDF/SHACL output is intentionally a handoff seed. Static validation does not execute SPARQL, run a standards-complete RDF parser, evaluate shapes with a SHACL engine, or claim OWL/data conformance. Domain experts must still validate URI policy, class/property semantics, named graph strategy, query behavior, SHACL policy, and Neptune loading posture before production use.

## Security Boundaries

Local workshop mode:

* Server binds to `127.0.0.1` in the documented startup command.
* Kuzu data and exports stay on the operator workstation.
* External communication is limited to the optional Claude API call when `ANTHROPIC_API_KEY` is set.
* Workflow evidence, snapshots, RDF exports, and reports may contain customer-provided claims or source schema details; treat the `exports/` directory as customer-sensitive workshop data.

Production handoff mode:

* Neptune deployment must use private subnets, security groups that allow the application tier only, AWS KMS encryption, IAM database authentication, and audit logging.
* S3 staging buckets for Bulk Loader must use Block Public Access, SSE-KMS, and a bucket policy that denies `aws:SecureTransport=false`.

## Authentication and Authorization

The local server is intended for single-operator workshops. For higher-risk environments:

* Loopback clients (`localhost`, `127.0.0.1`, `::1`) are allowed without a token.
* Set `ONTOFORGE_TOKEN` before starting the server when non-loopback clients can reach it.
* Set `ONTOFORGE_REQUIRE_TOKEN=1` only when localhost must also be token-gated.
* Open the viewer with `?token=<token>` when token authentication is required.
* Run the server behind TLS, for example:

```bash
uvicorn ontology_workshop.server:app \
  --host 127.0.0.1 --port 8000 \
  --ssl-keyfile key.pem --ssl-certfile cert.pem
```

## Input Validation

* Graph identifiers are restricted to ASCII letters, digits, and underscores, starting with a letter or underscore.
* User-submitted Cypher is read-only: write/DDL keywords such as `CREATE`, `MERGE`, `DELETE`, `DROP`, `ALTER`, and `SET` are rejected.
* Query result sets are capped to prevent accidental resource exhaustion.
* Export paths are constrained to `./exports`.

## Audit Logging

Set `ONTOFORGE_AUDIT_LOG` to a path under `./exports` or use the default `./exports/audit.log`. The server logs graph mutations, queries, WebSocket accepts/rejections, imports, and exports.

## Key Management

* `ANTHROPIC_API_KEY` must be supplied by environment variable only. Do not write it to source files, reports, or snapshots.
* Rotate the key after customer workshops involving sensitive material.
* For AWS deployment, use AWS Secrets Manager for application secrets and AWS KMS customer-managed keys for Neptune and S3 encryption.

## AI Security Controls

* Customer text is length-limited and control characters are removed before the optional LLM call.
* LLM JSON output is schema checked before graph insertion.
* Generated openCypher must pass the same read-only validation as user-entered queries.
* Domain experts must review AI-generated ontology decisions before production use.
* AI-ODLC extracted objects are candidate evidence until confirmed through an explicit decision; adversarial review makes ambiguity, contradiction, missing data, unsupported causality, event-modeling risk, over-modeling, and sensitivity concerns visible.
