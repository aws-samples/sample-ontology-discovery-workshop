# OntoForge

[English](./README.md) | [한국어](./README.ko.md) | [日本語](./README.ja.md)

OntoForge is a local workshop tool for building a graph model from business conversations and existing data. Participants work with their own AI assistant and use the browser to review the model.

## How the workshop works

The AI assistant asks about business scenarios, identifies entities and relationships, and updates the model as participants review it. Existing schemas and sample records help connect the discussion to the data.

The browser shows the model and workshop records. Participants can inspect properties, follow relationships, and check whether the graph answers their business questions.

## What participants review

- T-box: entity types, relationship types, properties, and identifiers.
- A-box: instances of those types and the relationships between them.
- Cypher queries: questions expressed as graph queries, with their results.
- Workshop records: decisions, source references, unresolved questions, and model changes.

Cypher is the language used to query and create property graphs. The graph model is the definition of the types, properties, and relationships. The workshop keeps that definition separate from instance data.

## Workshop results

The workshop produces a graph model, a record of the decisions behind it, and queries that participants used to check it. The local review app exports the model as JSON, PNG, SVG, and separate schema, data, or complete-model Cypher files.

## Start a workshop

Install the local review app and check the environment:

```bash
python3 -m venv viz-server/.venv
viz-server/.venv/bin/python -m pip install -r viz-server/requirements.txt
bash scripts/test-viz.sh
bash scripts/serve.sh
```

Open the server URL, normally `http://127.0.0.1:5173`. In your local AI tool, use `/onto-discover` or ask to start ontology discovery. The AI writes the model and workshop records under `ontology-docs/`; the browser displays the published model.

For the example model and workshop-day commands, see [Local workshop](./docs/LOCAL_WORKSHOP.md).

The existing API workshop and `$run-workshop` plugin remain available. Their server-owned sessions are separate from this file-based workflow; startup commands are in the same guide.

## Project documents

- [Local workshop](./docs/LOCAL_WORKSHOP.md)
- [Discovery workflow](./docs/ONTOLOGY_DISCOVERY.md)
- [Model format and Cypher export](./viz-server/README.md)
- [Workshop steps](./docs/AI_ODLC_WORKFLOW.md)
- [Application structure](./docs/DESIGN.md)
- [Workshop skills](./skills/WORKSHOP_SKILLS.md)
- [Security](./SECURITY.md)
- [Contributing](./CONTRIBUTING.md)
