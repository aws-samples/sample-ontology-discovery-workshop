---
description: "Run the OntoForge pre-export checklist and generate workshop deliverables"
---

# OntoForge Finalize

Finalize a workshop, verify gates, and generate report plus Neptune export artifacts.

## Steps

1. Load the current graph:
   ```bash
   curl -s http://localhost:8000/snapshot
   ```
2. Check and report the required gate status:
   - Modeling complete: entity types, relation types, instances, and edges exist.
   - Gate 1: every customer question has a verified openCypher query and focus metadata.
   - Gate 2: every entity/relation/data element has `보유`, `부분보유`, `미보유`, `파생(계산)`, or `모름`.
   - Gate 3: every available or partial data element has source/location/owner, and every missing element has an acquisition plan.
3. If any gate is incomplete, stop and ask for the missing input instead of exporting.
4. Build `/export/report` payload with Korean `descriptions`, `data_status`, and `action_items` unless the user selected `en` or `ja`.
5. Generate deliverables:
   ```bash
   curl -s -X POST http://localhost:8000/export/report -H 'Content-Type: application/json' -d @/tmp/ontoforge-report.json
   curl -s -X POST http://localhost:8000/export/neptune
   ```
6. Verify the expected outputs under `exports/report/` and `exports/neptune/`, then summarize:
   - report HTML/Markdown/DOCX paths
   - snapshot HTML/JSON paths
   - Neptune openCypher and bulk CSV paths
   - `/download/workshop.zip`

## Rules

- Do not say the workshop is complete until the checklist has no unresolved model gaps.
- If unresolved data gaps remain by design, include them as customer action items in the report.
- Customer-facing report text is Korean by default.
