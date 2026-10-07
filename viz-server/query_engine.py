from __future__ import annotations

import datetime
import importlib.util
import importlib.metadata
import json
import math
import re
import tempfile
import threading
import time
from pathlib import Path

from model import property_type, structural_errors
from quality import matches_type


MAX_QUERY_CHARACTERS = 10000
MAX_ROWS = 200
MAX_RESULT_BYTES = 1024 * 1024
DISALLOWED = {
    "ALTER", "ATTACH", "BEGIN", "CALL", "CHECKPOINT", "COMMIT", "COPY", "CREATE", "DELETE",
    "DETACH", "DROP", "EXPORT", "IMPORT", "INSTALL", "LOAD", "MERGE", "REMOVE", "ROLLBACK",
    "SET", "TRANSACTION", "UPDATE", "USE", "WRITE", "COMMENT", "MACRO",
}


def validate_query(query):
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARACTERS:
        raise ValueError("Cypher는 1~10,000자여야 합니다.")
    query = query.strip()
    output = []
    position = 0
    while position < len(query):
        character = query[position]
        if character in "'\"`":
            quote = character
            output.append(" ")
            position += 1
            while position < len(query):
                if query[position] == "\\":
                    position += 2
                elif query[position] == quote:
                    if position + 1 < len(query) and query[position + 1] == quote:
                        position += 2
                    else:
                        position += 1
                        break
                else:
                    position += 1
            else:
                raise ValueError("닫히지 않은 문자열 또는 식별자가 있습니다.")
        elif query.startswith("//", position):
            position = query.find("\n", position)
            if position < 0:
                position = len(query)
            output.append(" ")
        elif query.startswith("/*", position):
            end = query.find("*/", position + 2)
            if end < 0:
                raise ValueError("닫히지 않은 주석이 있습니다.")
            position = end + 2
            output.append(" ")
        else:
            output.append(character)
            position += 1
    scrubbed = "".join(output).strip()
    if scrubbed.endswith(";"):
        scrubbed = scrubbed[:-1].rstrip()
    if ";" in scrubbed:
        raise ValueError("한 번에 하나의 읽기 전용 쿼리만 실행할 수 있습니다.")
    words = re.findall(r"[A-Za-z_][A-Za-z_0-9]*", scrubbed.upper())
    forbidden = set(words) & DISALLOWED
    if forbidden:
        raise ValueError("읽기 전용 쿼리만 허용합니다: " + ", ".join(sorted(forbidden)))
    if not words or words[0] not in ("MATCH", "OPTIONAL", "WITH", "RETURN", "UNWIND", "EXPLAIN") or "RETURN" not in words:
        raise ValueError("MATCH / WITH / RETURN / UNWIND / EXPLAIN으로 시작하는 조회를 입력하세요.")
    return query


def _value(value, definition):
    if value is None:
        return None
    kind = property_type(definition)
    if kind.endswith("[]"):
        if not isinstance(value, list):
            raise ValueError(f"Expected {kind} array")
        return [_value(item, kind[:-2]) for item in value]
    if kind == "STRING":
        if not isinstance(value, str):
            raise ValueError(f"Expected STRING, got {type(value).__name__}")
    elif kind == "INT64" and (isinstance(value, bool) or not isinstance(value, int)):
        raise ValueError("Expected INT64")
    elif kind == "DOUBLE" and (isinstance(value, bool) or not isinstance(value, (int, float))):
        raise ValueError("Expected DOUBLE")
    elif kind == "BOOLEAN" and not isinstance(value, bool):
        raise ValueError("Expected BOOLEAN")
    elif kind == "DATE":
        return datetime.date.fromisoformat(value)
    elif kind == "TIMESTAMP":
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_value(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(nested) for nested in value]
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class QueryEngine:
    def __init__(self):
        try:
            self.version = importlib.metadata.version("kuzu")
        except importlib.metadata.PackageNotFoundError:
            self.version = None
        self.available = self.version == "0.11.3" and importlib.util.find_spec("kuzu") is not None
        self.lock = threading.Lock()
        self.database = None
        self.directory = None
        self.revision = None
        self.failed_revision = None
        self.build_error = None

    def capability(self, state):
        reason = "" if self.available else "검증된 Cypher 엔진 필요: python3 -m pip install -r viz-server/requirements.txt"
        if state["legacy"] or not state["schema"]["entities"]:
            reason = "로컬 AI가 명시적인 T-box와 A-box snapshot을 게시하면 Cypher 조회가 활성화됩니다."
        errors = structural_errors(state)
        if errors:
            reason = "그래프 구조 오류를 먼저 해결하세요: " + errors[0]
        if self.failed_revision == state["revision"]:
            reason = f"현재 모델의 Cypher 복제본을 만들 수 없습니다: {self.build_error}"
        if not reason:
            for kind in ("nodes", "edges"):
                for item in state["graphs"]["abox"][kind]:
                    data = item["data"]
                    definitions = state["schema"]["entities" if kind == "nodes" else "relations"][data["entity_type" if kind == "nodes" else "relation_type"]]["properties"]
                    for key, definition in definitions.items():
                        if not matches_type(data.get("props", {}).get(key), definition):
                            reason = f"속성 타입 오류를 먼저 해결하세요: {data['id']}.{key}"
                            break
        return {"available": not reason, "reason": reason, "engine": "Kuzu 0.11.3", "mode": "read-only", "scope": "게시된 A-box의 임시 조회 복제본", "max_rows": MAX_ROWS, "timeout_ms": 3000}

    def close(self):
        if self.database:
            self.database.close()
            self.database = None
        if self.directory:
            self.directory.cleanup()
            self.directory = None
        self.revision = None

    def _build(self, state):
        import kuzu

        if self.revision == state["revision"]:
            return
        if self.failed_revision == state["revision"]:
            raise ValueError(self.build_error)
        self.close()
        temporary = tempfile.TemporaryDirectory(prefix="ontology-query-")
        path = Path(temporary.name) / "projection.kuzu"
        database = None
        connection = None
        try:
            database = kuzu.Database(path, buffer_pool_size=64 * 1024 * 1024, max_num_threads=2)
            connection = kuzu.Connection(database, num_threads=2)
            connection.set_query_timeout(3000)
            for name, definition in state["schema"]["entities"].items():
                properties = definition["properties"]
                columns = ["`viz_id` STRING", "`display_label` STRING"]
                columns.extend(f"`{key}` {property_type(value)}" for key, value in properties.items())
                connection.execute(f"CREATE NODE TABLE `{name}`({', '.join(columns)}, PRIMARY KEY(`viz_id`))").close()
            for name, definition in state["schema"]["relations"].items():
                columns = ["`viz_id` STRING", "`display_label` STRING"]
                columns.extend(f"`{key}` {property_type(value)}" for key, value in definition["properties"].items())
                connection.execute(f"CREATE REL TABLE `{name}`(FROM `{definition['src']}` TO `{definition['dst']}`, {', '.join(columns)})").close()
            nodes = {item["data"]["id"]: item["data"] for item in state["graphs"]["abox"]["nodes"]}
            for data in nodes.values():
                name = data["entity_type"]
                definitions = state["schema"]["entities"][name]["properties"]
                values = {"viz_id": data["id"], "display_label": data["label"]}
                values.update({key: _value(data.get("props", {}).get(key), kind) for key, kind in definitions.items()})
                expressions = ", ".join(f"`{key}`: $property_{index}" for index, key in enumerate(values))
                parameters = {f"property_{index}": value for index, value in enumerate(values.values())}
                connection.execute(f"CREATE (node:`{name}` {{{expressions}}})", parameters).close()
            for item in state["graphs"]["abox"]["edges"]:
                data = item["data"]
                name = data["relation_type"]
                definition = state["schema"]["relations"][name]
                values = {"viz_id": data["id"], "display_label": data["label"]}
                values.update({key: _value(data.get("props", {}).get(key), kind) for key, kind in definition["properties"].items()})
                expressions = ", ".join(f"`{key}`: $property_{index}" for index, key in enumerate(values))
                parameters = {f"property_{index}": value for index, value in enumerate(values.values())}
                parameters.update({"source_id": data["source"], "target_id": data["target"]})
                connection.execute(f"MATCH (source:`{definition['src']}`), (target:`{definition['dst']}`) WHERE source.viz_id = $source_id AND target.viz_id = $target_id CREATE (source)-[:`{name}` {{{expressions}}}]->(target)", parameters).close()
            connection.close()
            connection = None
            database.close()
            database = None
            self.database = kuzu.Database(path, read_only=True, buffer_pool_size=64 * 1024 * 1024, max_num_threads=2)
            self.directory = temporary
            self.revision = state["revision"]
            self.failed_revision = None
            self.build_error = None
        except Exception as error:
            if connection:
                connection.close()
            if database:
                database.close()
            temporary.cleanup()
            self.failed_revision = state["revision"]
            self.build_error = str(error)[:1000]
            raise

    def execute(self, state, query, parameters=None):
        query = validate_query(query)
        if parameters is not None and not isinstance(parameters, dict):
            raise ValueError("parameters must be a JSON object")
        capability = self.capability(state)
        if not capability["available"]:
            raise ValueError(capability["reason"])
        import kuzu
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("다른 쿼리가 실행 중입니다. 완료 후 다시 시도하세요.")
        connection = None
        result = None
        try:
            self._build(state)
            connection = kuzu.Connection(self.database, num_threads=2)
            connection.set_query_timeout(3000)
            started = time.monotonic()
            result = connection.execute(query, parameters or {})
            if isinstance(result, list):
                for item in result:
                    item.close()
                result = None
                raise ValueError("여러 문장은 실행할 수 없습니다.")
            columns = result.get_column_names()
            rows = []
            total_bytes = 0
            truncated = False
            matched_ids = set()

            def collect(value):
                if isinstance(value, dict):
                    if "viz_id" in value:
                        matched_ids.add(str(value["viz_id"]))
                    for nested in value.values():
                        collect(nested)
                elif isinstance(value, list):
                    for nested in value:
                        collect(nested)

            while result.has_next():
                if len(rows) >= MAX_ROWS:
                    truncated = True
                    break
                row = json_value(result.get_next())
                total_bytes += len(json.dumps(row, ensure_ascii=False).encode("utf-8"))
                if total_bytes > MAX_RESULT_BYTES:
                    truncated = True
                    break
                collect(row)
                rows.append(row)
            return {"ok": True, "cypher": query, "columns": columns, "rows": rows, "count": len(rows), "truncated": truncated, "elapsed_ms": round((time.monotonic() - started) * 1000, 1), "matched_ids": sorted(matched_ids), "revision": state["revision"], "scope": capability["scope"]}
        finally:
            if result is not None:
                result.close()
            if connection is not None:
                connection.close()
            self.lock.release()
