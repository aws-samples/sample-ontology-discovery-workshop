# Local API operations

Use the installed plugin helper instead of hand-building curl commands:

```bash
PLUGIN_ROOT="<installed ontoforge-workshop plugin root>"
API="$PLUGIN_ROOT/scripts/api.py"
"$API" GET /workflow/state
"$API" POST /workflow/start --data '{"language":"ko","scope":"one-day ontology discovery","reset":false}'
```

The helper reads `ONTOFORGE_URL` and `ONTOFORGE_TOKEN`; it defaults to the
repository-local loopback server at `http://127.0.0.1:8000` without authentication.

Normal customer answers should go through the current Markdown form and `forms.py`,
not through a hand-built `/workflow/answer` request. The direct example below is a
fallback reference for debugging or non-form imports.

## Capture an answer

Always copy `current_stage` from fresh server state. Supply only evidence supported by
the answer. Collection names in `extracted` are plural workflow collection names.

```bash
"$API" POST /workflow/answer --data '{
  "stage":"inception",
  "role":"customer",
  "status":"candidate",
  "source":"codex_plugin",
  "text":"The original user answer",
  "extracted":{
    "user_stories":[{
      "actor":"Quality manager",
      "goal":"Trace defect impact faster",
      "decision":"Identify affected lots",
      "success_metric":"Reduce investigation time from days to hours",
      "scope":"One representative traceability scenario in this workshop",
      "priority":"high",
      "status":"candidate"
    }]
  }
}'
```

Other supported collections include `domain_events`, `competency_questions`,
`model_candidates`, `data_sources`, `field_mappings`, `assumptions`,
`contradictions`, `review_findings`, `risks`, `action_items`, `validation_queries`,
and `rdf_decisions`.

## Advance

```bash
"$API" POST /workflow/advance --data '{"force":false,"actor":"codex-facilitator"}'
```

Forced movement is exceptional and needs the user's supplied reason:

```bash
"$API" POST /workflow/advance --data '{
  "force":true,
  "reason":"User-provided auditable reason of meaningful length",
  "actor":"codex-facilitator"
}'
```

## Decide evidence

Read the collection and exact item ID first. Every operation needs a meaningful note.

```bash
"$API" POST /workflow/items/review_findings/finding-001/decision --data '{
  "action":"resolve",
  "changes":{},
  "note":"The domain owner clarified the term and approved the recorded definition.",
  "actor":"customer-via-codex"
}'
```

For high/critical acceptance include an owner-linked action:

```json
{
  "action": "accept",
  "note": "Accepted as a bounded follow-up rather than hidden risk.",
  "actor": "customer-via-codex",
  "linked_action": {
    "text": "Validate the unresolved source mapping after the workshop",
    "owner": "data-team"
  }
}
```

## Apply a reviewed T-Box

Only after user confirmation:

```bash
"$API" POST /entity --data '{
  "name":"Product",
  "properties":{"id":"STRING"},
  "primary_key":"id"
}'
"$API" POST /relation --data '{
  "name":"AFFECTED_BY",
  "src":"Product",
  "dst":"SupplierLot",
  "cardinality":"N:M",
  "properties":{}
}'
```

Ensure matching model candidates already carry story/event/question/data-source IDs;
otherwise the server will correctly keep the traceability gate closed.

## Review, query, validate, and hand off

```bash
"$API" POST /workflow/review --data '{}'
"$API" POST /query --data '{
  "question":"Exact stored competency question text",
  "cypher":"Exact stored openCypher seed"
}'
"$API" POST /workflow/validate --data '{
  "outdir":"./exports/report/validation",
  "base_iri":"https://example.com/domain/"
}'
"$API" POST /export/report --data '{"lang":"ko"}'
```

Review and validation are user-triggered bounded actions. Never poll, automatically
retry, or silently rerun them.
