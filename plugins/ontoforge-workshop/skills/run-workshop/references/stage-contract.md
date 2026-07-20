# AI-ODLC stage contract

Always use the current `/workflow/state` gate checks as the executable authority. This
reference explains intent; it must not replace or duplicate server gate evaluation.

| Stage | Collect | Do not infer |
|---|---|---|
| `inception` | High-priority story with actor, goal, decision, measurable success, and one-day scope | Business metric, scope, or actor authority |
| `discovery` | One real start-to-finish narrative linked to a priority story; definitions or explicit ambiguity decisions | Formal model from nouns alone |
| `event_discovery` | Trigger, state change, and node/relation/property classification for important events, or an explicit no-event rationale | Causality or event-node need from temporal wording alone |
| `story_to_question` | Prioritized competency questions, story links, and expected answer shapes | A question the user did not need answered |
| `model_synthesis` | Question-linked entity/event/relation/property candidates and a user-reviewed T-Box | Keys, cardinalities, or relation direction without evidence |
| `data_grounding` | Actual source fields, owners, freshness, mappings, readiness, sensitivity, and owned gap actions | Fields or availability not present in supplied structures |
| `adversarial_review` | One current review covering ambiguity, contradiction, causality, event modeling, over-modeling, and sensitivity; explicit dispositions | Acceptance of AI-generated findings |
| `validation_handoff` | Exact query evidence, owned actions, current artifacts, optional requested static RDF validation | Production readiness, SPARQL execution, SHACL conformance, or OWL reasoning |

## Evidence rules

- Send answers only for the actual current stage.
- Let the server compute checks and progress after every mutation.
- Advance only one adjacent stage at a time.
- Require an explicit user-provided reason for force-next.
- Keep AI extraction candidate-level until a human decision is captured.
- Record a meaningful decision note for every confirm, accept, reject, revise,
  resolve, start, update, or merge operation.
- Accept high/critical review evidence only with an owner-linked action.
- Preserve conflicting non-empty values as conflicts until explicitly revised or
  merged.

## Workshop pacing

The target is one day, not exhaustive enterprise modeling. Prefer one representative
scenario, a small prioritized question set, the minimum connected model that answers
those questions, and explicit follow-up actions for everything else.
