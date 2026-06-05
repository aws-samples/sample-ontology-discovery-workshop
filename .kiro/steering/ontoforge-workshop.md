# OntoForge Workshop Steering

Kiro loads `.kiro/steering/` files automatically. Use this as the always-on entry rule for this repository; the detailed workflow remains in `.kiro/skills/ontoforge-workshop/SKILL.md`.

## Activation

Apply these rules when the user asks for OntoForge, an ontology workshop, T-Box/A-Box modeling, live graph visualization, report export, Neptune export, or snapshot restore. For unrelated coding tasks, keep these rules as background context only.

## Operating Rules

1. The web app is a viewer and local orchestrator. The agent extracts entities, relations, properties, openCypher, and report descriptions; do not rely on the browser mock extractor as the workshop source of truth.
2. Use `http://localhost:8000` or `http://127.0.0.1:8000` for local-only workshops. Loopback access should not require auth unless the user explicitly sets `ONTOFORGE_REQUIRE_TOKEN=1` or asks to test token mode. If localhost returns `401 Unauthorized`, check for an old token-protected server process and restart local uvicorn without token enforcement before changing code.
3. Keep the terminology exact:
   - T-Box = schema/types: entity types and relation types.
   - A-Box = instances: instance nodes and instance edges.
   - UI labels should say "엔티티 타입 (T-Box)", "관계 타입 (T-Box)", "인스턴스 노드 (A-Box)", and "인스턴스 엣지 (A-Box)".
4. Follow the gate sequence in the skill: modeling -> Gate 1 query coverage -> Gate 2 data status -> Gate 3 data location -> architecture/export. Do not skip a gate because the graph looks plausible.
5. Before final export, report the stage/gate checklist, customer question coverage, unresolved model/data gaps, and next actions. Write the customer-facing report in Korean unless the user selected another report language.
6. Mask customer personal or sensitive data before sending it to external services. Use local/offline extraction unless third-party LLM use has explicit approval.
7. For code changes, run at least `python -m compileall src`; for UI label or WebSocket changes, also verify the local page in a browser when practical.

## Kiro Behavior

Do not switch to a separate Kiro Spec Mode workflow unless the user explicitly asks for it. This project already has a workshop skill and live server workflow; use the skill as the detailed procedure.
