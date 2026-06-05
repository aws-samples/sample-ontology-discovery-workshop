# Workshop Skill Specification

The conversation layer receives customer answers, runs the skills below in stages, and applies each JSON result to OntoForge through REST endpoints. Each skill returns **JSON only**: no preamble, no Markdown.

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

Apply through `POST /query`. Include the original `question` to receive evidence text.

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

## Evolution Loop

When the T-Box changes during conversation, rerun skills 1 and 2 so the graph, documentation, visualization, and Neptune export stay synchronized.
