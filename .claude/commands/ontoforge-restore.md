---
description: "Restore an OntoForge workshop from a snapshot JSON or standalone snapshot HTML"
---

# OntoForge Restore

Restore a previous workshop into the local live viewer.

## Steps

1. Ensure the server is running at `http://localhost:8000`; use `/ontoforge-start` behavior if needed.
2. Prefer `workshop_snapshot.json`. Restore it directly:
   ```bash
   curl -s -X POST http://localhost:8000/import -H 'Content-Type: application/json' -d @workshop_snapshot.json
   ```
3. If the user only has `workshop_snapshot.html`, extract the embedded snapshot first:
   ```bash
   python3 -c "import re,sys; h=open('workshop_snapshot.html',encoding='utf-8').read(); m=re.search(r'window.__ONTOFORGE_SNAPSHOT__ = (\\{.*?\\});',h,re.S); open('/tmp/ontoforge-snapshot.json','w',encoding='utf-8').write(m.group(1))"
   curl -s -X POST http://localhost:8000/import -H 'Content-Type: application/json' -d @/tmp/ontoforge-snapshot.json
   ```
4. Report restored counts from the response: entity types, relation types, nodes, edges, narrations, verified queries, and skipped edges.
5. If `skipped_edges > 0`, ask the user whether to inspect snapshot consistency before continuing the workshop.

## Rules

- Do not reset the workshop before import unless the user explicitly asks or the import endpoint itself performs the reset.
- Keep all T-Box/A-Box terminology consistent when summarizing the restored state.
