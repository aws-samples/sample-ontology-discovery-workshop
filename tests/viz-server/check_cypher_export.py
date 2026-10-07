import copy
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import kuzu


root = Path(__file__).resolve().parents[2]
output_directory = root / "output" / "viz-server-tests"
output_directory.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root / "viz-server"))
from cypher_export import export_cypher, literal
from model import normalize
from server import VizServer
from store import GraphStore, atomic_json, read_json


checks = []


def check(name, value):
    if not value:
        raise AssertionError(name)
    checks.append(name)


def rejects(action):
    try:
        action()
        return False
    except (ValueError, RuntimeError, OSError):
        return True


def execute(connection, query):
    result = connection.execute(query)
    results = result if isinstance(result, list) else [result]
    try:
        return [entry.get_next() for entry in results for _ in range(entry.get_num_tuples())]
    finally:
        for entry in results:
            entry.close()


document = read_json(root / "examples/payment-settlement/workshop-model.json")
state = normalize(document)
check("export generation is deterministic", export_cypher(state) == export_cypher(state))
check("unknown scope rejected", rejects(lambda: export_cypher(state, "anything")))
check("legacy graph does not invent schema", rejects(lambda: export_cypher(normalize({"elements": {"nodes": [], "edges": []}}))))
schema = export_cypher(state, "schema")
data = export_cypher(state, "data")
whole = export_cypher(state, "model")
check("schema uses declared domain primary key", "PRIMARY KEY(`merchant_id`)" in schema["content"])
check("schema includes relationship endpoint types and multiplicity", "FROM `Payment` TO `Settlement`" in schema["content"] and "MANY_ONE" in schema["content"])
check("schema exports definition metadata", "COMMENT ON TABLE `Merchant`" in schema["content"] and "trace_links" in schema["content"])
check("schema contains no instance inserts", "CREATE (node:" not in schema["content"])
check("data contains no table creation", "CREATE NODE TABLE" not in data["content"])
check("whole model has schema and instance statements", "CREATE NODE TABLE" in whole["content"] and "CREATE (node:" in whole["content"])
check("export uses a transaction", whole["content"].startswith("BEGIN TRANSACTION;") and whole["content"].endswith("COMMIT;\n"))

with tempfile.TemporaryDirectory(prefix="ontology-cypher-export-") as directory:
    folder = Path(directory)
    database = kuzu.Database(folder / "roundtrip.kuzu", buffer_pool_size=32 * 1024 * 1024, max_num_threads=2)
    connection = kuzu.Connection(database)
    try:
        execute(connection, schema["content"])
        check("schema round trip creates all 8 tables", len(execute(connection, "CALL show_tables() RETURN *")) == 8)
        check("schema alone has no instances", execute(connection, "MATCH (node) RETURN count(node)") == [[0]])
        execute(connection, data["content"])
        check("data round trip recreates 7 nodes", execute(connection, "MATCH (node) RETURN count(node)") == [[7]])
        check("data round trip recreates 7 edges", execute(connection, "MATCH ()-[edge]->() RETURN count(edge)") == [[7]])
        check("domain aggregate query returns exact original result", execute(connection, document["queries"][0]["cypher"]) == [["북촌 서점", 120000.0], ["제주 로스터리", 36000.0]])
        table_metadata = execute(connection, "CALL show_tables() RETURN *")
        merchant = next(row for row in table_metadata if row[1] == "Merchant")
        check("T-box metadata survives database catalog storage", json.loads(merchant[-1])["trace_links"] == ["story-001", "DDL.merchants"])
    finally:
        connection.close()
        database.close()

    values = {
        "id": "quoted 'key'; MATCH (node) DELETE node; //\n한글\\path",
        "text": "O'Brien \"quote\" \\ backslash\nnewline\ttab\rreturn\x00null\x01control 😀",
        "enabled": False,
        "counter": -9223372036854775808,
        "amount": 12.125,
        "created": "2026-10-07",
        "observed": "2026-10-07T09:30:45.123456",
        "tags": ["한국어", "semi;colon", "quote'", None],
        "empty_numbers": [],
        "optional_text": None,
        "moments": ["2026-10-07T00:00:00"],
    }
    definitions = {
        "id": "STRING", "text": "STRING", "enabled": "BOOLEAN", "counter": "INT64", "amount": "DOUBLE",
        "created": "DATE", "observed": "TIMESTAMP", "tags": "STRING[]", "empty_numbers": "INT64[]", "optional_text": "STRING", "moments": "TIMESTAMP[]",
    }
    edge_values = {"message": "quoted ' relationship\n\\", "weights": [1.5, 2.5], "accepted": True}
    typed_model = {
        "metadata": {"title": "Typed export"},
        "tbox": {"entities": {"Record": {"primary_key": "id", "properties": definitions, "trace_links": ["evidence:typed"], "description": "Schema 'description'\nsecond line"}}, "relations": {"LINK": {"src": "Record", "dst": "Record", "cardinality": "1:1", "properties": {"message": "STRING", "weights": "DOUBLE[]", "accepted": "BOOLEAN"}}}},
        "snapshot": {"nodes": [{"data": {"id": "Record:one", "label": "문자열 '검증'", "etype": "Record", "props": values, "trace_links": ["evidence:row"]}}], "edges": [{"data": {"id": "LINK:one", "source": "Record:one", "target": "Record:one", "rtype": "LINK", "props": edge_values, "trace_links": ["evidence:link"]}}]},
    }
    typed = normalize(typed_model)
    database = kuzu.Database(folder / "typed.kuzu", buffer_pool_size=32 * 1024 * 1024, max_num_threads=2)
    connection = kuzu.Connection(database)
    try:
        execute(connection, export_cypher(typed)["content"])
        row = execute(connection, "MATCH (node:Record) RETURN node")[0][0]
        check("escaped strings and control characters round trip", row["text"] == values["text"] and row["id"] == values["id"])
        check("unicode display label retained", row["display_label"] == "문자열 '검증'")
        check("booleans int64 and doubles retained", row["enabled"] is False and row["counter"] == values["counter"] and row["amount"] == 12.125)
        check("dates and timestamps retained", str(row["created"]) == values["created"] and row["observed"].isoformat() == values["observed"])
        check("arrays empty arrays and null retained", row["tags"] == values["tags"] and row["empty_numbers"] == [] and row["optional_text"] is None)
        check("timestamp array retained", row["moments"][0].isoformat() == values["moments"][0])
        relation = execute(connection, "MATCH ()-[edge:LINK]->() RETURN edge")[0][0]
        check("relationship properties retained", all(relation[key] == value for key, value in edge_values.items()))
        check("quoted input cannot execute Cypher", execute(connection, "MATCH (node) RETURN count(node)") == [[1]])
    finally:
        connection.close()
        database.close()

    no_key = copy.deepcopy(document)
    no_key["tbox"]["entities"]["Merchant"].pop("primary_key")
    check("missing declared primary key uses stable viz_id", "CREATE NODE TABLE `Merchant`" in export_cypher(normalize(no_key), "schema")["content"] and "PRIMARY KEY(`viz_id`)" in export_cypher(normalize(no_key), "schema")["content"])
    invalid = copy.deepcopy(document)
    invalid["snapshot"]["nodes"][0]["data"]["props"]["extra_value"] = 123
    check("undeclared properties cannot disappear silently", rejects(lambda: export_cypher(normalize(invalid))))
    check("schema-only export works with invalid instances", bool(export_cypher(normalize(invalid), "schema")["content"]))
    invalid = copy.deepcopy(document)
    invalid["snapshot"]["nodes"][0]["data"]["props"].pop("merchant_id")
    check("missing domain primary key rejected", rejects(lambda: export_cypher(normalize(invalid))))
    invalid = copy.deepcopy(document)
    invalid["snapshot"]["nodes"][1]["data"]["props"]["merchant_id"] = "m-001"
    check("duplicate domain primary key rejected", rejects(lambda: export_cypher(normalize(invalid))))
    invalid = copy.deepcopy(document)
    invalid["snapshot"]["nodes"][2]["data"]["props"]["amount"] = "not a number"
    check("wrong typed value rejected", rejects(lambda: export_cypher(normalize(invalid))))
    invalid = copy.deepcopy(document)
    invalid["tbox"]["entities"]["Merchant"]["properties"]["merchant_id"] = "BOOLEAN"
    check("unsupported primary key type rejected with clear error", rejects(lambda: export_cypher(normalize(invalid), "schema")))
    check("empty typed array literal", literal([], "STRING[]") == "CAST([], 'STRING[]')")

    store = GraphStore(folder / "workshop" / "viz-runtime")
    published = store.publish(document, "test", "Export test")
    original_bytes = (store.data_root / "current.json").read_bytes()
    server = VizServer(("127.0.0.1", 0), store.data_root, root / "viz-server")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def get(url):
        try:
            with urlopen(base + url, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    try:
        for scope in ("schema", "data", "model"):
            status, result = get(f"/api/export/cypher?scope={scope}&revision={published['revision']}")
            check(f"HTTP {scope} export", status == 200 and result["filename"] == f"ontology-{scope}.cypher" and result["content"].endswith("COMMIT;\n"))
        check("HTTP stale model export rejected", get("/api/export/cypher?scope=model&revision=old")[0] == 409)
        check("HTTP invalid scope rejected", get("/api/export/cypher?scope=unsupported")[0] == 422)
        check("HTTP export does not modify published model", original_bytes == (store.data_root / "current.json").read_bytes())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    command = [sys.executable, str(root / "viz-server/agent.py"), "--data-dir", str(store.data_root), "export-cypher"]
    output = folder / "schema.cypher"
    completed = subprocess.run(command + ["--scope", "schema", "--output", str(output)], capture_output=True, text=True)
    check("CLI writes named .cypher file", completed.returncode == 0 and "CREATE NODE TABLE" in output.read_text())
    saved = output.read_bytes()
    completed = subprocess.run(command + ["--scope", "schema", "--output", str(output)], capture_output=True, text=True)
    check("CLI preserves existing output", completed.returncode != 0 and output.read_bytes() == saved)
    completed = subprocess.run(command + ["--scope", "data"], capture_output=True, text=True)
    check("CLI stdout export", completed.returncode == 0 and completed.stdout.startswith("BEGIN TRANSACTION;"))
    completed = subprocess.run(command + ["--scope", "model", "--output", str(folder / "wrong.md")], capture_output=True, text=True)
    check("CLI rejects unexpected extension", completed.returncode != 0 and not (folder / "wrong.md").exists())

result = {"passed": len(checks), "checks": checks}
(output_directory / "cypher-export-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
