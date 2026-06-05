---
description: "Start or recover the local OntoForge workshop server"
---

# OntoForge Start

Start or recover the local OntoForge server for a localhost-only workshop.

## Steps

1. Work from the repository root.
2. Check whether the server responds:
   ```bash
   curl -i http://localhost:8000/snapshot
   ```
3. If the response is `200`, report that the app is ready at `http://localhost:8000`.
4. If loopback returns `401 Unauthorized`, assume a token-protected server is already running. Unless the user asked for token mode, restart the local uvicorn process for this workspace without `ONTOFORGE_TOKEN` and without `ONTOFORGE_REQUIRE_TOKEN`.
5. If the server is not running, start it bound to loopback:
   ```bash
   PYTHONPATH=src .venv/bin/uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   ```
6. Verify both endpoints:
   ```bash
   curl -i http://localhost:8000/
   curl -s http://localhost:8000/snapshot
   ```
7. Tell the user to open `http://localhost:8000`. Do not ask for an auth token for a localhost-only workshop.

## Notes

- If `.venv/bin/uvicorn` is missing, install dependencies from `requirements.txt` first.
- Do not use `ONTOFORGE_FRESH=1` for normal restarts. It deletes `workshop.kuzu`; use `/reset` only when the operator explicitly wants a blank workshop.
- The server autosaves workshop state to `exports/session/workshop_snapshot.json` and restores it on startup when the graph is empty.
- Use token mode only when the user explicitly requests shared-network or auth testing.
- For actual workshop operation, follow `.claude/skills/ontoforge-workshop/SKILL.md`.
