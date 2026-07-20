---
name: run-workshop
description: Run or resume a domain-neutral, one-day OntoForge AI-ODLC ontology discovery workshop through stage-by-stage Markdown answer forms in an OntoForge repository checkout. Use when the user asks to start, test, rehearse, facilitate, resume, fill forms for, review, validate, or hand off the OntoForge workflow with user stories, domain narratives, events, competency questions, model candidates, data structures, adversarial review, RDF/SHACL notes, or the terminal cockpit.
---

# Run an OntoForge workshop

Operate as the AI facilitator. Treat the local OntoForge server as the workflow
state and gate authority. Conduct the conversation in the user's language and keep
graph identifiers in English.

## Establish the repository session

1. Resolve the repository root with `git rev-parse --show-toplevel`. Verify it contains
   `src/ontology_workshop/server.py`; the marketplace plugin is an agent workflow, not
   a standalone installation of the OntoForge application.
2. Set `PLUGIN_ROOT` from the installed skill path shown in the session context and run
   `"$PLUGIN_ROOT/scripts/check-runtime.sh" "$PROJECT_ROOT"`.
3. If the server is unavailable, start it as a persistent loopback process from the
   repository root: `PYTHONPATH=src .venv/bin/python -m uvicorn
   ontology_workshop.server:app --host 127.0.0.1 --port 8000`. Never set
   `ONTOFORGE_FRESH` automatically.
4. Set `API="$PLUGIN_ROOT/scripts/api.py"` and `FORMS="$PLUGIN_ROOT/scripts/forms.py"`.
   Read authoritative state with `"$API" GET /workflow/state`.
5. Do not reset an existing session unless the user explicitly asks. If requested,
   use `"$API" POST /reset --data '{}'` and state that existing workshop state will
   be discarded.
6. Run `"$FORMS" sync`. Tell the user the returned `answers/<stage>.md` path and
   ask them to edit it, then say `작성 완료` in the CLI.
7. Tell the user that the browser is at `http://127.0.0.1:8000` and the optional
   human TUI starts with `PYTHONPATH=src .venv/bin/python -m ontology_workshop.tui
   --url http://127.0.0.1:8000`.

Never automate the TUI. Use the plugin API helper for agent actions; the TUI is a
human cockpit over the same server-owned state.

## Use stage forms as the primary interaction

Do not print a multi-field questionnaire in the CLI. Generate or sync only the current
stage form under `answers/`. Never pre-create all remaining forms: later forms must
reflect the actual server state when their stage begins.

When the user says `작성 완료`, `done`, or an equivalent:

1. Run `"$FORMS" status`. If required sections are empty, cite only those headings
   and ask the user to update the same file. Do not reproduce the whole form.
2. Read the form. Identify ambiguity, contradiction, unsupported inference, or a
   value needed to construct structured evidence. Ask at most one focused follow-up in
   the CLI. If needed, write the clarified answer into the same Markdown file only
   after the user confirms the wording.
3. Construct conservative structured `extracted` JSON from the form in
   `answers/.extracted.json`. Preserve unknowns as unknown; never invent business
   facts, owners, metrics, keys, cardinalities, source fields, sensitivity, or RDF
   policy.
4. Run `"$FORMS" submit --extracted-file answers/.extracted.json`. The helper reads
   the Markdown itself, prevents unchanged duplicate submission, sends a revised
   previously submitted form through `/workflow/clarify`, and deletes the temporary
   extracted JSON after a successful submission.
5. Run `"$FORMS" sync` again. If the current gate is still blocked, refer the user
   to the updated server-state section and ask one question for the smallest remaining
   gap. Do not turn each heading into a separate CLI question.
6. Advance only to the immediate next stage after the gate passes. Then run
   `"$FORMS" sync` to create the next stage form and give its path to the user.

Markdown files are source evidence and an editing surface, not canonical workflow
state. The server remains authoritative. Never edit the form's YAML `stage`,
`ontoforge_form`, or `ONTOFORGE:SERVER-STATE` markers by hand. Never delete or
overwrite an existing answer form to restart a stage.

Use candidate status for AI-extracted evidence. Do not confirm your own inference.
When confirmation, rejection, revision, resolution, or acceptance is required, present
the concrete evidence item to the user, then call its decision endpoint with the
user's meaningful note. High/critical acceptance requires an owner-linked action.

Read [stage-contract.md](references/stage-contract.md) before facilitating the first
stage. Read [form-workflow.md](references/form-workflow.md) before using a form. Read
[api-operations.md](references/api-operations.md) before the first mutation or whenever
a payload is uncertain.

## Model and data boundary

Keep model candidates separate from confirmed graph schema. During Model Synthesis:

- link every candidate to a story, event, question, or data-source ID;
- link every expected answer-shape candidate to its competency-question ID;
- for a multi-element answer shape, include a question-linked relation with valid
  candidate endpoints;
- show the proposed T-Box to the user before applying `/entity` and `/relation`;
- retain naming conflicts for decision instead of silently merging them.

During Data Grounding, accept actual schemas, CSV headers, API payloads, catalog
extracts, or explicit source descriptions. Map only real source fields to existing
candidate/T-Box targets. Missing or unknown mappings need an owner-tagged action.

## Bounded review and validation

Run `/workflow/review` once after material story, event, model, and data evidence exists,
or when the user explicitly requests it. Do not automatically rerun it. Ask the user
to dispose generated items explicitly; do not treat generation as acceptance.

Run `/workflow/validate` only when the user requests the one bounded static RDF
handoff check. State that it does not execute SPARQL, evaluate SHACL engine
conformance, perform OWL reasoning, or establish production readiness. Do not poll or
retry automatically.

At handoff, execute the exact stored openCypher seed for every high-priority question
with its exact question text. Ad-hoc success, `RETURN 1`, aliases, comments, strings,
or disconnected Cartesian patterns do not qualify. Generate the report package only
after the user requests handoff, then re-read gates and accurately report unresolved
evidence.

## Interaction contract

- Match the user's language. Use English PascalCase entity names, English
  UPPER_SNAKE_CASE relation names, and valid Kuzu property identifiers.
- Keep normal CLI replies to a short reflection plus a form path or one ambiguity
  question. Put structured multi-field input in the Markdown form, not the CLI.
- Explain a blocking API or gate error concretely; do not bypass it silently.
- Never claim production ontology, RDF, SHACL, security, or Neptune readiness from a
  one-day workshop.
- Do not enable an external LLM or transmit customer data outside the local session
  without explicit authorization.
- Preserve the latest repository-local state; do not edit application source as
  part of workshop facilitation.
