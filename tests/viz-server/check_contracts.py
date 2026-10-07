import copy
import importlib
import json
import sys
import tempfile
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


root = Path(__file__).resolve().parents[2]
output_directory = root / "output" / "viz-server-tests"
output_directory.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root / "viz-server"))
from model import normalize, structural_errors
from quality import analyze
from query_engine import QueryEngine, validate_query
from server import VizServer
from store import GraphStore, atomic_json, read_json


results = []


def check(name, value):
    if not value:
        raise AssertionError(name)
    results.append(name)


def rejects(action):
    try:
        action()
        return False
    except (ValueError, RuntimeError, TypeError):
        return True


model = read_json(root / "examples/payment-settlement/workshop-model.json")
state = normalize(model)
check("explicit T-box and A-box contract", state["counts"] == {"entity_types": 5, "relation_types": 3, "nodes": 7, "edges": 7})
check("valid structure", not structural_errors(state))
check("legacy format remains explicit and query-disabled", normalize({"elements": {"nodes": [], "edges": []}})["legacy"])
check("array document rejected", rejects(lambda: normalize([])))
invalid = copy.deepcopy(model)
invalid["snapshot"]["nodes"][0]["data"]["trace_links"] = "not-an-array"
check("invalid traces rejected", rejects(lambda: normalize(invalid)))
invalid = copy.deepcopy(model)
invalid["tbox"]["entities"]["Merchant"]["properties"]["viz_id"] = "STRING"
check("projection reserved fields rejected", rejects(lambda: normalize(invalid)))
invalid = copy.deepcopy(model)
invalid["tbox"]["relations"]["MAKES"]["cardinality"] = "arbitrary"
check("invalid cardinality rejected", rejects(lambda: normalize(invalid)))
check("missing schema evidence and singleton warnings", {"orphan", "singleton"} <= {entry["code"] for entry in analyze(state)["findings"]})

minimal = copy.deepcopy(model)
minimal["metadata"]["depth"] = "minimal"
check("minimal depth skips singleton", "singleton" not in {entry["code"] for entry in analyze(normalize(minimal))["findings"]})
suppressed = copy.deepcopy(model)
finding = next(entry for entry in analyze(state)["findings"] if entry["code"] == "singleton")
suppressed["quality_decisions"] = {finding["id"]: {"status": "suppressed", "revision": state["revision"], "actor": "reviewer", "reason": "Explicit review-only reference"}}
check("same-version reasoned suppression", next(entry for entry in analyze(normalize(suppressed))["findings"] if entry["id"] == finding["id"])["status"] == "suppressed")
suppressed["snapshot"]["nodes"][0]["data"]["label"] = "New label"
check("old suppression invalidated after graph revision", next(entry for entry in analyze(normalize(suppressed))["findings"] if entry["id"] == finding["id"])["status"] == "open")
suppressed["quality_decisions"][finding["id"]]["revision"] = normalize(suppressed)["revision"]
suppressed["quality_decisions"][finding["id"]]["reason"] = ""
check("suppression without reason rejected", next(entry for entry in analyze(normalize(suppressed))["findings"] if entry["id"] == finding["id"])["status"] == "open")

invalid = copy.deepcopy(model)
invalid["snapshot"]["nodes"][0]["data"]["props"]["name"] = 12
invalid["snapshot"]["nodes"][0]["data"]["props"]["extra"] = True
invalid["snapshot"]["nodes"][2]["data"]["props"]["status"] = "UNKNOWN"
invalid["snapshot"]["nodes"][1]["data"]["props"]["merchant_id"] = "m-001"
invalid["snapshot"]["nodes"][4]["data"]["props"].pop("payment_id")
codes = {entry["code"] for entry in analyze(normalize(invalid))["findings"]}
check("property types enum extra properties duplicate and missing keys", {"type-name", "undeclared-extra", "enum-status", "duplicate-key", "missing-key"} <= codes)
invalid = copy.deepcopy(model)
invalid["snapshot"]["edges"].append({"data": {"id": "second-merchant", "source": "Merchant:m-002", "target": "Payment:p-001", "rtype": "MAKES"}})
check("cardinality violation detected", "cardinality-MAKES" in {entry["code"] for entry in analyze(normalize(invalid))["findings"]})
invalid["snapshot"]["edges"].append({"data": {"id": "dangling", "source": "Merchant:missing", "target": "Payment:p-001", "rtype": "MAKES"}})
check("dangling edge reported", "dangling-edge" in {entry["code"] for entry in analyze(normalize(invalid))["findings"]})
invalid["snapshot"]["edges"].append({"data": {"id": "wrong-type", "source": "Payment:p-001", "target": "Merchant:m-001", "rtype": "MAKES"}})
check("endpoint type mismatch reported", "relation-endpoint" in {entry["code"] for entry in analyze(normalize(invalid))["findings"]})

hub = {"metadata": {"depth": "comprehensive"}, "tbox": {"entities": {}, "relations": {}}, "snapshot": {"nodes": [], "edges": []}}
hub["tbox"]["entities"]["Hub"] = {"properties": {"kind": {"type": "STRING", "enum": ["one", "two", "three", "four", "five"]}}, "conditional_relationships": ["Evidence of enum-dependent relation patterns"], "bounded_context": "hub", "trace_links": ["evidence:hub"]}
for number in range(10):
    name = f"Type{number}"
    hub["tbox"]["entities"][name] = {"bounded_context": f"context-{number}", "trace_links": [f"evidence:{number}"]}
    hub["tbox"]["relations"][f"CONNECTS{number}"] = {"src": "Hub", "dst": name}
for number in range(3):
    hub["tbox"]["relations"][f"LOOP{number}"] = {"src": "Hub", "dst": "Hub"}
codes = {entry["code"] for entry in analyze(normalize(hub))["findings"]}
check("hot node multi context recursion discriminator dead end heuristics", {"hot-node", "multi-bc", "deep-recursion", "type-discriminator", "dead-end"} <= codes)
hub["tbox"]["entities"]["Type0"]["label"] = "Shipment"
hub["tbox"]["entities"]["Type1"]["label"] = "Shipments"
hub["tbox"]["relations"]["SAME0"] = {"src": "Type0", "dst": "Hub", "label": "related"}
hub["tbox"]["relations"]["SAME1"] = {"src": "Type1", "dst": "Hub", "label": "related"}
legacy_duplicates = {"metadata": {"depth": "comprehensive"}, "elements": {"nodes": [{"data": {"id": "one", "label": "Shipment", "type": "entity", "trace_links": ["evidence:one"]}}, {"data": {"id": "two", "label": "Shipments", "type": "entity", "trace_links": ["evidence:two"]}}, {"data": {"id": "hub", "label": "Merchant", "type": "entity", "trace_links": ["evidence:hub"]}}], "edges": [{"data": {"id": "first", "source": "one", "target": "hub", "type": "related-to"}}, {"data": {"id": "second", "source": "two", "target": "hub", "type": "related-to"}}]}}
check("symmetric duplicate heuristic", "symmetric-duplicate" in {entry["code"] for entry in analyze(normalize(legacy_duplicates))["findings"]})
legacy_isa = {"metadata": {}, "elements": {"nodes": [{"data": {"id": "base", "label": "Base", "type": "entity", "trace_links": ["base"]}}, {"data": {"id": "child", "label": "Child", "type": "entity", "trace_links": ["child"]}}], "edges": [{"data": {"id": "isa", "source": "child", "target": "base", "type": "is-a"}}]}}
check("inheritance does not produce false singleton", "singleton" not in {entry["code"] for entry in analyze(normalize(legacy_isa))["findings"]})

for query in ["MATCH (node) DELETE node RETURN node", "RETURN 1; CREATE (node)", "CALL show_tables() RETURN *", "LOAD FROM '/etc/passwd' RETURN *", "WITH 1 AS value INSTALL httpfs RETURN value", "RETURN 'unterminated", "RETURN 1 /* unterminated"]:
    check(f"query blocked: {query[:40]}", rejects(lambda query=query: validate_query(query)))
for query in ["RETURN 'DELETE; CREATE' AS text", "// CREATE\nRETURN 1", "/* DELETE */ MATCH (node) RETURN node LIMIT 1", "RETURN 1;"]:
    check(f"quoted or commented query accepted: {query[:40]}", bool(validate_query(query)))

engine = QueryEngine()
try:
    query = engine.execute(state, model["queries"][0]["cypher"])
    check("real aggregate Cypher results", query["rows"] == [["북촌 서점", 120000.0], ["제주 로스터리", 36000.0]])
    path = engine.execute(state, model["queries"][1]["cypher"])
    check("real paths returned and mapped to graph ids", path["count"] == 3 and "Merchant:m-001" in path["matched_ids"] and "edge:payment-1-settlement" in path["matched_ids"])
    parameterized = engine.execute(state, model["queries"][2]["cypher"], {"min_amount": 50000})
    check("Cypher parameter binding", parameterized["count"] == 1)
    bounded = engine.execute(state, "UNWIND range(1, 300) AS number RETURN number")
    check("query row cap and truncation", bounded["count"] == 200 and bounded["truncated"])
    nonfinite = engine.execute(state, "RETURN 1.0 / 0 AS infinity, 0.0 / 0 AS not_number")
    check("non-finite query values serialize safely", nonfinite["rows"] == [["inf", "nan"]])
    check("write query cannot reach engine", rejects(lambda: engine.execute(state, "MATCH (node) DETACH DELETE node RETURN 1")))
    kuzu = importlib.import_module("kuzu")
    connection = kuzu.Connection(engine.database)
    try:
        check("engine database is physically read-only", rejects(lambda: connection.execute("CREATE NODE TABLE Unauthorized(id STRING, PRIMARY KEY(id))")))
    finally:
        connection.close()
    engine.lock.acquire()
    try:
        check("concurrent query rejected", rejects(lambda: engine.execute(state, "RETURN 1")))
    finally:
        engine.lock.release()
finally:
    engine.close()

with tempfile.TemporaryDirectory(prefix="ontology-contract-") as folder:
    folder = Path(folder)
    store = GraphStore(folder / "ontology-docs" / "viz-runtime")
    published = store.publish(model, "verification", "Initial model")
    second = copy.deepcopy(model)
    second["snapshot"]["nodes"][0]["data"]["label"] = "Revised label"
    check("update requires expected version", rejects(lambda: store.publish(second, "verification", "Missing expected revision")))
    updated = store.publish(second, "verification", "Actual update", published["document_revision"])
    check("immutable previous revision preserved", len(store.history()) == 2 and store.history()[0]["changes"][0]["before"]["label"] == "북촌 서점")
    check("stale revision rejected", rejects(lambda: store.publish(model, "verification", "Stale write", published["document_revision"])))
    check("quality fingerprint excludes decision metadata", normalize(model)["revision"] == normalize({**model, "quality_decisions": {"irrelevant": {}}})["revision"])
    before = (store.data_root / "current.json").read_bytes()
    invalid = copy.deepcopy(model)
    invalid["snapshot"]["nodes"].append(copy.deepcopy(invalid["snapshot"]["nodes"][0]))
    check("publish rejects duplicate ids without touching current", rejects(lambda: store.publish(invalid, "verification", "Bad model", updated["document_revision"])) and before == (store.data_root / "current.json").read_bytes())
    (folder / "outside.md").write_text("not exposed")
    (store.data_root.parent / "notes.md").write_text("valid workshop note")
    server = VizServer(("127.0.0.1", 0), store.data_root, root / "viz-server")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def request(path, payload=None, headers=None, raw=False):
        request_headers = {"Content-Type": "application/json", "X-Ontology-Token": server.token}
        request_headers.update(headers or {})
        data = payload if raw else None if payload is None else json.dumps(payload).encode()
        try:
            with urlopen(Request(base + path, data=data, headers=request_headers), timeout=10) as response:
                body = response.read()
                return response.status, json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body
        except HTTPError as error:
            return error.code, json.loads(error.read())

    try:
        check("health unverified before browser report", request("/health")[1]["status"] == "degraded")
        check("state API", request("/api/state")[1]["counts"]["nodes"] == 7)
        check("API history and quality", len(request("/api/history")[1]["entries"]) == 2 and request("/api/quality")[1]["open_count"] >= 1)
        for path in ["/server.py", "/.venv/pyvenv.cfg", "/lib/../server.py", "/source/%2e%2e/outside.md", "/data/%2e%2e/notes.md", "/data/revisions/private.json"]:
            check(f"file boundary {path}", request(path)[0] in (403, 404))
        check("workshop Markdown source", request("/source/notes.md")[1] == b"valid workshop note")
        check("DNS rebinding host rejected", request("/api/state", headers={"Host": "attacker.invalid"})[0] == 403)
        query_body = {"cypher": "RETURN 1 AS value", "revision": updated["revision"]}
        check("POST requires session token", request("/api/query", query_body, {"X-Ontology-Token": "bad"})[0] == 403)
        check("cross origin POST rejected", request("/api/query", query_body, {"Origin": "http://attacker.invalid"})[0] == 403)
        check("array JSON rejected", request("/api/query", [1, 2])[0] == 400)
        check("NaN JSON rejected", request("/api/query", b'{"value":NaN}', raw=True)[0] == 400)
        check("malformed body rejected", request("/api/query", b"broken", raw=True)[0] == 400)
        check("stale query rejected", request("/api/query", {**query_body, "revision": "old"})[0] == 409)
        check("actual HTTP Cypher", request("/api/query", query_body)[1]["rows"] == [[1]])
        check("write HTTP Cypher blocked", request("/api/query", {**query_body, "cypher": "CREATE (node) RETURN node"})[0] == 422)
        check("query audit contains success and failure", len(request("/api/queries")[1]["entries"]) == 2)
        check("model mutation endpoint absent", request("/api/model", {})[0] == 404)
        feedback = {"nodeId": "Merchant:m-001", "note": "Consider actual source evidence", "revision": updated["revision"]}
        check("feedback accepted", request("/feedback", feedback)[0] == 200)
        check("feedback append-only", request("/feedback", {**feedback, "note": "Second review"})[0] == 200 and (store.data_root.parent / "feedback-pending.md").read_text().count("## Feedback") == 2)
        check("invalid feedback target rejected", request("/feedback", {**feedback, "nodeId": "not-present"})[0] == 400)
        report = {"ok": True, "revision": updated["revision"], "view": "tbox", "nodes_rendered": 5, "edges_rendered": 3, "extensions": {"fcose": True, "cose-bilkent": True}}
        check("render report saved", request("/render-status", report)[0] == 200)
        check("health verified after matching successful render", request("/health")[1]["status"] == "ok")
        request("/render-status", {**report, "ok": False})
        check("failed render degrades health", request("/health")[1]["status"] == "degraded")
        request("/render-status", {**report, "nodes_rendered": 1})
        check("partial render degrades health", request("/health")[1]["status"] == "degraded")
        request("/render-status", {**report, "extensions": {}})
        check("missing extensions degrade health", request("/health")[1]["status"] == "degraded")
        check("bad render field rejected", request("/render-status", {**report, "nodes_rendered": "oops"})[0] == 400)
        atomic_json(store.data_root / "render-status.json", [])
        check("malformed report cannot crash health", request("/health")[1]["status"] == "degraded")
        check("browser reads and queries preserve current model", before == (store.data_root / "current.json").read_bytes())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

report = {"passed": len(results), "checks": results}
(output_directory / "backend-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
