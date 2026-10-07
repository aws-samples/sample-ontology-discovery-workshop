# Local model review checks

Run from the repository root after installing `viz-server/requirements.txt`:

```bash
bash scripts/test-viz.sh
```

The Python checks use temporary databases and ephemeral HTTP ports. They cover model publication, quality analysis, read-only queries, HTTP boundaries, and Cypher export round trips. Reports are written under `output/viz-server-tests/`.

## Browser checks

Use a separate example session. The browser checks submit test feedback and execute read-only queries, so do not point them at a real workshop session.

```bash
python3 viz-server/agent.py --data-dir output/browser-check/viz-runtime publish \
  --file examples/payment-settlement/workshop-model.json \
  --actor browser-check --summary 'Browser verification fixture'
bash scripts/serve.sh --data-dir output/browser-check/viz-runtime --no-browser
```

With Playwright CLI installed, run these commands in another terminal from the repository root. Use the URL printed by the server:

```bash
playwright-cli -s=ontology-review open http://127.0.0.1:5173
playwright-cli -s=ontology-review snapshot
playwright-cli -s=ontology-review run-code --filename tests/viz-server/check_browser.js
playwright-cli -s=ontology-review snapshot
playwright-cli -s=ontology-review run-code --filename tests/viz-server/check_export_browser.js
playwright-cli -s=ontology-review close
```

The scripts use the opened page's origin and save screenshots and downloads under `output/viz-server-tests/`. They check panels, filters, layouts, query results, model inspectors, feedback, exports, and responsive rendering.
