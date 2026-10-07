from __future__ import annotations

import datetime
import json
import math
from collections import Counter

from model import property_type, structural_errors
from quality import analyze, matches_type


SCOPES = {"schema", "data", "model"}
MULTIPLICITIES = {
    "1:1": "ONE_ONE",
    "1:N": "ONE_MANY",
    "1:M": "ONE_MANY",
    "N:1": "MANY_ONE",
    "M:1": "MANY_ONE",
    "N:M": "MANY_MANY",
    "M:N": "MANY_MANY",
    "N:N": "MANY_MANY",
}


def string_literal(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def literal(value, definition):
    kind = property_type(definition)
    if value is None:
        return "NULL"
    if not matches_type(value, definition):
        raise ValueError(f"값이 {kind} 타입과 일치하지 않습니다: {value!r}")
    if kind.endswith("[]"):
        elements = ", ".join(literal(item, kind[:-2]) for item in value)
        return f"CAST([{elements}], {string_literal(kind)})"
    if kind == "STRING":
        return string_literal(value)
    if kind == "BOOLEAN":
        return "true" if value else "false"
    if kind == "INT64":
        return str(value)
    if kind == "DOUBLE":
        if not math.isfinite(value):
            raise ValueError("유한한 숫자만 내보낼 수 있습니다.")
        return repr(float(value))
    if kind == "DATE":
        return f"date({string_literal(datetime.date.fromisoformat(value).isoformat())})"
    if kind == "TIMESTAMP":
        return f"timestamp({string_literal(datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat())})"
    raise ValueError(f"내보낼 수 없는 타입입니다: {kind}")


def primary_key(definition):
    return definition.get("primary_key") or "viz_id"


def validate_export(state, scope):
    if scope not in SCOPES:
        raise ValueError("scope는 schema, data, model 중 하나여야 합니다.")
    if state["legacy"] or not state["schema"]["entities"]:
        raise ValueError("Cypher로 내보내려면 T-box의 엔티티 타입을 먼저 정의하세요.")
    errors = structural_errors(state)
    if scope == "schema":
        errors = [error for error in errors if error.startswith("tbox:")]
    if errors:
        raise ValueError("; ".join(errors[:10]))
    for name, definition in state["schema"]["entities"].items():
        key = primary_key(definition)
        kind = property_type(definition["properties"][key]) if key != "viz_id" else "STRING"
        if kind == "BOOLEAN" or kind.endswith("[]"):
            raise ValueError(f"{name}.{key}: 로컬 Cypher 스키마의 기본 키로 {kind}를 사용할 수 없습니다.")
    if scope == "schema":
        return
    findings = analyze(state)["findings"]
    errors = [finding for finding in findings if finding["severity"] == "error" or finding["code"].startswith("undeclared-")]
    if errors:
        raise ValueError("내보내기 전에 데이터 정의를 확인하세요: " + "; ".join(f"{finding['title']} ({', '.join(finding['element_ids'])})" for finding in errors[:10]))
    sources = Counter()
    targets = Counter()
    for item in state["graphs"]["abox"]["edges"]:
        data = item["data"]
        relation = data["relation_type"]
        sources[(relation, data["source"])] += 1
        targets[(relation, data["target"])] += 1
    for name, definition in state["schema"]["relations"].items():
        multiplicity = MULTIPLICITIES[definition["cardinality"]]
        for counter, restricted in ((sources, multiplicity.endswith("_ONE")), (targets, multiplicity.startswith("ONE_"))):
            if restricted and any(count > 1 for (relation, _), count in counter.items() if relation == name):
                raise ValueError(f"{name}: {definition['cardinality']} 관계의 한쪽 끝에 여러 관계가 있습니다.")


def schema_statements(state):
    statements = []
    for name, definition in sorted(state["schema"]["entities"].items()):
        columns = [f"`{key}` {property_type(value)}" for key, value in sorted(definition["properties"].items())]
        columns.extend(["`viz_id` STRING", "`display_label` STRING"])
        columns.append(f"PRIMARY KEY(`{primary_key(definition)}`)")
        statements.append(f"CREATE NODE TABLE `{name}` ({', '.join(columns)});")
        metadata = json.dumps(definition, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        statements.append(f"COMMENT ON TABLE `{name}` IS {string_literal(metadata)};")
    for name, definition in sorted(state["schema"]["relations"].items()):
        columns = [f"FROM `{definition['src']}` TO `{definition['dst']}`"]
        columns.extend(f"`{key}` {property_type(value)}" for key, value in sorted(definition["properties"].items()))
        columns.extend(["`viz_id` STRING", "`display_label` STRING", MULTIPLICITIES[definition["cardinality"]]])
        statements.append(f"CREATE REL TABLE `{name}` ({', '.join(columns)});")
        metadata = json.dumps(definition, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        statements.append(f"COMMENT ON TABLE `{name}` IS {string_literal(metadata)};")
    return statements


def property_map(data, definition):
    properties = {"viz_id": string_literal(data["id"]), "display_label": string_literal(data["label"])}
    properties.update({key: literal(data.get("props", {}).get(key), kind) for key, kind in definition["properties"].items()})
    return "{" + ", ".join(f"`{key}`: {value}" for key, value in sorted(properties.items())) + "}"


def data_statements(state):
    statements = []
    entities = state["schema"]["entities"]
    relations = state["schema"]["relations"]
    nodes = {item["data"]["id"]: item["data"] for item in state["graphs"]["abox"]["nodes"]}
    for element_id in sorted(nodes):
        data = nodes[element_id]
        name = data["entity_type"]
        statements.append(f"CREATE (node:`{name}` {property_map(data, entities[name])});")
    for item in sorted(state["graphs"]["abox"]["edges"], key=lambda entry: entry["data"]["id"]):
        data = item["data"]
        name = data["relation_type"]
        definition = relations[name]
        source = nodes[data["source"]]
        target = nodes[data["target"]]
        source_key = primary_key(entities[definition["src"]])
        target_key = primary_key(entities[definition["dst"]])
        source_value = string_literal(source["id"]) if source_key == "viz_id" else literal(source["props"][source_key], entities[definition["src"]]["properties"][source_key])
        target_value = string_literal(target["id"]) if target_key == "viz_id" else literal(target["props"][target_key], entities[definition["dst"]]["properties"][target_key])
        statements.append(f"MATCH (source:`{definition['src']}` {{`{source_key}`: {source_value}}}), (target:`{definition['dst']}` {{`{target_key}`: {target_value}}}) CREATE (source)-[:`{name}` {property_map(data, definition)}]->(target);")
    return statements


def export_cypher(state, scope="model"):
    validate_export(state, scope)
    statements = []
    if scope in ("schema", "model"):
        statements.extend(schema_statements(state))
    if scope in ("data", "model"):
        statements.extend(data_statements(state))
    content = "\n\n".join(["BEGIN TRANSACTION;", *statements, "COMMIT;"]) + "\n"
    return {"filename": f"ontology-{scope}.cypher", "scope": scope, "dialect": "kuzu", "revision": state["revision"], "statement_count": len(statements), "content": content}
