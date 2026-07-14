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
* assumptions, risks, review findings, and action items.

`POST /workflow/answer` is the main entry point. It records a claim, conservatively extracts workflow objects from natural language or JSON, updates gate coverage, generates the next focused question, and broadcasts the new workflow state to the browser cockpit. It does not claim production ontology readiness.

The browser cockpit shows current stage, gates, next question, evidence counts, detailed evidence cards, and actions for answer submission, gate advancement, next-question refresh, and adversarial review generation.

## Export and Handoff Artifacts

Report export packages the property graph, workflow state, verified openCypher evidence, Neptune openCypher/Bulk Loader files, standalone snapshot, and RDF handoff files. RDF handoff includes `ontology.ttl`, `instances.ttl`, `ontology.jsonld`, `shapes.ttl`, `queries.sparql`, `rdf_mapping.md`, and `neptune_rdf_handoff.md`.

RDF/SHACL output is intentionally a handoff seed. Domain experts must validate URI policy, class/property semantics, named graph strategy, SPARQL behavior, SHACL constraints, and Neptune loading posture before production use.

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
* AI-ODLC extracted objects are candidate evidence until confirmed; adversarial review should make ambiguity, missing data, and unsupported assumptions visible.
