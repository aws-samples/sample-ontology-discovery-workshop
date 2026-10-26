"""
구조 품질 점검 로직 (복제본).

원본: viz-server/model.py, viz-server/quality.py
이 파일은 두 모듈의 로직을 스킬 폴더 안으로 복제한 것이다. viz-server 경로에
의존하지 않고 스킬 하나로 완결 실행하기 위함이다.

주의: 원본(viz-server/model.py, viz-server/quality.py)이 바뀌면 이 복제본도
수동으로 맞춰야 한다. 동작 기준은 복제 시점의 원본이다.
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# model.py 복제분
# ---------------------------------------------------------------------------
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
PROPERTY_TYPES = {"STRING", "INT64", "DOUBLE", "BOOLEAN", "DATE", "TIMESTAMP"}
RESERVED_PROPERTIES = {"viz_id", "display_label"}
CARDINALITIES = {"N:M", "M:N", "N:N", "1:N", "1:M", "N:1", "M:1", "1:1"}


def fingerprint(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]


def identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid type/property identifier: {value!r}")
    return value


def property_type(definition):
    value = definition.get("type", "STRING") if isinstance(definition, dict) else definition
    value = str(value).upper()
    if value == "BOOL":
        value = "BOOLEAN"
    if value.removesuffix("[]") not in PROPERTY_TYPES:
        raise ValueError(f"Unsupported property type: {value}")
    return value


def _elements(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain nodes and edges")
    output = {"nodes": [], "edges": []}
    for kind in output:
        rows = value.get(kind, [])
        if not isinstance(rows, list):
            raise ValueError(f"{label}.{kind} must be an array")
        for item in rows:
            if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
                raise ValueError(f"Every {label}.{kind} item must have a data object")
            entry = copy.deepcopy(item)
            data = entry["data"]
            if not isinstance(data.get("id"), str) or not data["id"]:
                raise ValueError(f"Every {label}.{kind} item needs a nonempty string id")
            if not isinstance(data.get("label", ""), str):
                raise ValueError(f"Label for {data['id']} must be a string")
            for field in ("trace_links", "personas", "key_attributes", "source_files", "synonyms"):
                if field in data and (not isinstance(data[field], list) or not all(isinstance(value, str) for value in data[field])):
                    raise ValueError(f"{data['id']}.{field} must be an array of strings")
            if "props" in data and not isinstance(data["props"], dict):
                raise ValueError(f"{data['id']}.props must be an object")
            if "properties" in data and not isinstance(data["properties"], dict):
                raise ValueError(f"{data['id']}.properties must be an object")
            if "parent" in data and not isinstance(data["parent"], str):
                raise ValueError(f"{data['id']}.parent must be a string")
            for field in ("type", "phase_introduced", "bounded_context", "source_file", "entity_type", "relation_type", "etype", "rtype"):
                if field in data and not isinstance(data[field], str):
                    raise ValueError(f"{data['id']}.{field} must be a string")
            if kind == "edges" and not all(isinstance(data.get(key), str) for key in ("source", "target")):
                raise ValueError(f"Edge {data['id']} needs source and target ids")
            data.setdefault("label", data["id"])
            data.setdefault("trace_links", [])
            output[kind].append(entry)
    return output


def normalize(document):
    if not isinstance(document, dict):
        raise ValueError("Graph document must be a JSON object")
    metadata = document.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    metadata = copy.deepcopy(metadata)
    metadata.setdefault("title", "Ontology Discovery")
    metadata.setdefault("phase", "워크숍 준비")
    metadata.setdefault("depth", "standard")
    if "demo" in metadata and not isinstance(metadata["demo"], bool):
        raise ValueError("metadata.demo must be boolean")
    for field in ("title", "phase", "depth"):
        if not isinstance(metadata[field], str):
            raise ValueError(f"metadata.{field} must be a string")
    if metadata["depth"] not in ("minimal", "standard", "comprehensive"):
        raise ValueError("metadata.depth must be minimal, standard, or comprehensive")
    schema = copy.deepcopy(document.get("tbox", {"entities": {}, "relations": {}}))
    if not isinstance(schema, dict):
        raise ValueError("tbox must be an object")
    for kind in ("entities", "relations"):
        if not isinstance(schema.setdefault(kind, {}), dict):
            raise ValueError(f"tbox.{kind} must be an object keyed by type name")
        for name, definition in schema[kind].items():
            identifier(name)
            if not isinstance(definition, dict):
                raise ValueError(f"tbox.{kind}.{name} must be an object")
            definition["name"] = name
            if kind == "relations":
                cardinality = definition.setdefault("cardinality", "N:M")
                if not isinstance(cardinality, str) or cardinality.upper() not in CARDINALITIES:
                    raise ValueError(f"{name}.cardinality must be one of {sorted(CARDINALITIES)}")
                definition["cardinality"] = cardinality.upper()
            properties = definition.setdefault("properties", {})
            if not isinstance(properties, dict):
                raise ValueError(f"{name}.properties must be an object")
            for key, value in properties.items():
                identifier(key)
                if key in RESERVED_PROPERTIES:
                    raise ValueError(f"Property {key} is reserved for the visualization projection")
                property_type(value)
                if isinstance(value, dict) and "enum" in value and not isinstance(value["enum"], list):
                    raise ValueError(f"{name}.{key}.enum must be an array")
            if kind == "entities":
                primary_key = definition.get("primary_key")
                if primary_key:
                    identifier(primary_key)
                    if primary_key not in properties:
                        properties[primary_key] = "STRING"
            else:
                identifier(definition.get("src"))
                identifier(definition.get("dst"))
    shared_names = set(schema["entities"]) & set(schema["relations"])
    if shared_names:
        raise ValueError(f"Entity and relation type names must be distinct: {sorted(shared_names)}")
    legacy = "tbox" not in document and "snapshot" not in document
    if legacy:
        schema_graph = _elements(document.get("elements", {"nodes": [], "edges": []}), "elements")
        instances = {"nodes": [], "edges": []}
    else:
        schema_graph = {"nodes": [], "edges": []}
        for name, definition in schema["entities"].items():
            data = copy.deepcopy(definition)
            data.update({"id": f"type:{name}", "label": definition.get("label", name), "type": "entity", "entity_type": name, "phase_introduced": "05"})
            data.setdefault("trace_links", [])
            schema_graph["nodes"].append({"data": data})
        for name, definition in schema["relations"].items():
            data = copy.deepcopy(definition)
            data.update({"id": f"relation:{name}", "source": f"type:{definition['src']}", "target": f"type:{definition['dst']}", "label": definition.get("label", name), "type": name, "relation_type": name})
            data.setdefault("trace_links", [])
            schema_graph["edges"].append({"data": data})
        schema_graph = _elements(schema_graph, "tbox graph")
        instances = _elements(document.get("snapshot", {"nodes": [], "edges": []}), "snapshot")
        for element in instances["nodes"]:
            data = element["data"]
            data["entity_type"] = data.get("etype", data.get("entity_type", ""))
            data.setdefault("type", "instance")
            definition = schema["entities"].get(data["entity_type"], {})
            data.setdefault("bounded_context", definition.get("bounded_context", ""))
        for element in instances["edges"]:
            data = element["data"]
            data["relation_type"] = data.get("rtype", data.get("relation_type", data.get("label", "")))
            data.setdefault("type", data["relation_type"])
    graph_revision = fingerprint({"schema": schema, "tbox": schema_graph, "abox": instances})
    decisions = document.get("quality_decisions", {})
    if not isinstance(decisions, dict):
        raise ValueError("quality_decisions must be an object")
    queries = document.get("queries", [])
    if not isinstance(queries, list) or any(not isinstance(item, dict) or not isinstance(item.get("cypher"), str) for item in queries):
        raise ValueError("queries must contain objects with cypher strings")
    if len(queries) > 100:
        raise ValueError("At most 100 query presets are supported")
    for query in queries:
        if len(query["cypher"]) > 10000 or not isinstance(query.get("parameters", {}), dict):
            raise ValueError("Query presets need up to 10,000 Cypher characters and object parameters")
    return {
        "metadata": metadata, "schema": schema, "graphs": {"tbox": schema_graph, "abox": instances},
        "revision": graph_revision, "document_revision": fingerprint(document), "legacy": legacy,
        "queries": queries, "quality_decisions": decisions,
        "counts": {"entity_types": len(schema["entities"]), "relation_types": len(schema["relations"]), "nodes": len(instances["nodes"]), "edges": len(instances["edges"])},
    }


# ---------------------------------------------------------------------------
# quality.py 복제분
# ---------------------------------------------------------------------------
def matches_type(value, definition):
    if value is None:
        return True
    kind = property_type(definition)
    if kind.endswith("[]"):
        return isinstance(value, list) and all(matches_type(item, kind[:-2]) for item in value)
    if kind == "STRING":
        return isinstance(value, str)
    if kind == "INT64":
        return isinstance(value, int) and not isinstance(value, bool) and -(2**63) <= value < 2**63
    if kind == "DOUBLE":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if kind == "BOOLEAN":
        return isinstance(value, bool)
    if kind in ("DATE", "TIMESTAMP"):
        if not isinstance(value, str):
            return False
        try:
            (datetime.date if kind == "DATE" else datetime.datetime).fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
    return False


def analyze(state):
    findings = []
    notes = []
    depth = state["metadata"].get("depth", "standard")

    def add(code, view, element_ids, title, detail, recommendation, severity="warning", evidence=None):
        entry_id = f"{code}-{fingerprint([view, sorted(element_ids)])[:12]}"
        decision = state["quality_decisions"].get(entry_id, {})
        valid_decision = isinstance(decision, dict) and decision.get("revision") == state["revision"] and bool(str(decision.get("reason", "")).strip()) and bool(str(decision.get("actor", "")).strip())
        status = decision.get("status", "open") if valid_decision else "open"
        if status not in ("accepted", "suppressed"):
            status = "open"
        findings.append({"id": entry_id, "code": code, "view": view, "element_ids": element_ids, "severity": severity, "title": title, "detail": detail, "recommendation": recommendation, "evidence": evidence or {}, "status": status, "decision": decision if valid_decision else None})

    for view, graph in state["graphs"].items():
        all_elements = graph["nodes"] + graph["edges"]
        identifiers = Counter(item["data"]["id"] for item in all_elements)
        for element_id, count in identifiers.items():
            if count > 1:
                add("duplicate-id", view, [element_id], "중복 ID", f"같은 ID가 {count}번 등장합니다.", "로컬 AI에서 고유 ID로 수정하세요.", "error")
        nodes = {item["data"]["id"]: item["data"] for item in graph["nodes"]}
        incoming = Counter()
        outgoing = Counter()
        all_incoming = Counter()
        all_outgoing = Counter()
        contexts = defaultdict(set)
        loops = defaultdict(set)
        signatures = defaultdict(set)
        targets = defaultdict(set)
        sources = defaultdict(set)
        duplicates = defaultdict(list)
        for element in graph["edges"]:
            data = element["data"]
            source, target = data["source"], data["target"]
            relation = data.get("relation_type", data.get("type", "related-to"))
            if source not in nodes or target not in nodes:
                add("dangling-edge", view, [data["id"]], "끝점이 없는 관계", f"{source} → {target}", "누락된 노드를 게시하거나 관계를 정정하세요.", "error")
                continue
            duplicates[(source, relation, target, fingerprint(data.get("props", {})))].append(data["id"])
            targets[(relation, source)].add(target)
            sources[(relation, target)].add(source)
            if relation.lower().replace("_", "-") != "trace-link":
                all_outgoing[source] += 1
                all_incoming[target] += 1
            if relation.lower().replace("_", "-") not in ("is-a", "trace-link"):
                outgoing[source] += 1
                incoming[target] += 1
                for current, neighbor in ((source, target), (target, source)):
                    if nodes[neighbor].get("bounded_context") and nodes[neighbor].get("bounded_context") != nodes[current].get("bounded_context"):
                        contexts[current].add(nodes[neighbor]["bounded_context"])
                    signatures[current].add(("out" if current == source else "in", relation, nodes[neighbor].get("entity_type", nodes[neighbor].get("type", ""))))
            if source == target:
                loops[source].add(relation)
            if view == "abox":
                definition = state["schema"]["relations"].get(relation)
                if not definition:
                    add("unknown-relation", view, [data["id"]], "정의되지 않은 관계 타입", relation, "T-box 관계 정의를 먼저 확인하세요.", "error")
                elif (nodes[source].get("entity_type"), nodes[target].get("entity_type")) != (definition["src"], definition["dst"]):
                    add("relation-endpoint", view, [data["id"], source, target], "관계의 타입 제약 불일치", f"{relation}: {definition['src']} → {definition['dst']}", "인스턴스 타입 또는 관계 정의를 확인하세요.", "error")
        for duplicate_ids in duplicates.values():
            if len(duplicate_ids) > 1:
                add("duplicate-relation", view, duplicate_ids, "동일 관계 중복 후보", "시작점·끝점·타입·속성이 같습니다.", "독립적인 관계인지 확인 후 로컬 AI에서 정리하세요.")
        candidates = [data for data in nodes.values() if data.get("type") not in ("concept", "bounded-context", "persona", "activity", "domain-event", "command", "policy", "read-model", "data-source", "work-object", "aggregate")]
        degrees = {data["id"]: incoming[data["id"]] + outgoing[data["id"]] for data in candidates}
        total = sum(degrees.values())
        average = total / len(degrees) if degrees else 0
        for data in candidates:
            element_id = data["id"]
            degree = degrees[element_id]
            reference = data.get("reference") or data.get("external_reference")
            if not reference and degree >= 4 and degree >= average * 3 and degree >= total * .25:
                add("hot-node", view, [element_id], "연결 집중 후보", f"non-is-a degree {degree}; 평균 {average:.1f}", "본질적 허브인지, 여러 책임이 혼재했는지 도메인 전문가와 확인하세요.", evidence={"degree": degree, "average": round(average, 2), "contexts": sorted(contexts[element_id])})
            if not data.get("trace_links"):
                add("orphan", view, [element_id], "근거 추적 링크 없음", data.get("label", element_id), "원본 자료·스토리·이벤트의 근거 ID를 추가하거나 예외 사유를 기록하세요.", "info")
            if depth != "minimal":
                if not reference and len(contexts[element_id]) >= 4:
                    add("multi-bc", view, [element_id], "여러 컨텍스트에 책임 집중", ", ".join(sorted(contexts[element_id])), "컨텍스트별 책임 분리 후보를 검토하세요.")
                if all_incoming[element_id] + all_outgoing[element_id] == 0 and not reference:
                    add("singleton", view, [element_id], "고립 노드", "도메인 관계가 없습니다. 추적 링크는 도메인 관계에 포함하지 않습니다.", "독립적인 개념인지 또는 관계가 누락됐는지 확인하세요.")
                if len(loops[element_id]) >= 3:
                    add("deep-recursion", view, [element_id], "여러 종류의 자기 참조", ", ".join(sorted(loops[element_id])), "관계를 별도 연결 엔티티로 표현할 필요가 있는지 검토하세요.")
            if depth == "comprehensive":
                if all_incoming[element_id] and not all_outgoing[element_id] and not reference and not data.get("terminal"):
                    add("dead-end", view, [element_id], "종료점 확인 필요", "들어오는 관계만 있습니다.", "정상적인 최종 상태라면 terminal 또는 검토 사유를 기록하세요.", "info")
                definitions = data.get("properties", {})
                enums = {name: definition["enum"] for name, definition in definitions.items() if isinstance(definition, dict) and isinstance(definition.get("enum"), list) and len(definition["enum"]) >= 5}
                if enums and data.get("conditional_relationships"):
                    add("type-discriminator", view, [element_id], "타입 구분 속성에 책임 집중 후보", ", ".join(enums), "enum별로 달라지는 속성·관계를 서브타입으로 분리할지 확인하세요.", evidence={"enums": enums})
            if data.get("health_warning"):
                add("agent-warning", view, [element_id], "로컬 AI가 기록한 품질 경고", str(data.get("health_warning_type", "검토 필요")), str(data.get("health_recommendation", "AI 도구에서 원문 근거와 해결 방안을 확인하세요.")))
        if depth == "comprehensive":
            if len(candidates) > 500:
                notes.append(f"{view}: 유사 엔티티 비교는 500개 이하에서만 수행합니다.")
            else:
                for index, first in enumerate(candidates):
                    for second in candidates[index + 1:]:
                        first_set, second_set = signatures[first["id"]], signatures[second["id"]]
                        if not first_set or not second_set:
                            continue
                        similarity = len(first_set & second_set) / len(first_set | second_set)
                        first_label, second_label = first["label"].casefold(), second["label"].casefold()
                        synonym = second["label"] in first.get("synonyms", []) or first["label"] in second.get("synonyms", [])
                        if similarity >= .8 and (synonym or SequenceMatcher(None, first_label, second_label).ratio() >= .85):
                            add("symmetric-duplicate", view, [first["id"], second["id"]], "유사 엔티티 통합 후보", f"관계 패턴 유사도 {similarity:.0%}", "동의어인지 확인하세요. 자동 통합하지 않습니다.")
        if view == "abox":
            keys = defaultdict(list)
            for data in nodes.values():
                definition = state["schema"]["entities"].get(data.get("entity_type"))
                if not definition:
                    add("unknown-entity", view, [data["id"]], "정의되지 않은 엔티티 타입", data.get("entity_type", ""), "T-box 타입을 먼저 정의하세요.", "error")
                    continue
                properties = data.get("props", {})
                primary_key = definition.get("primary_key")
                if primary_key:
                    if properties.get(primary_key) is None:
                        add("missing-key", view, [data["id"]], "식별자 값 누락", primary_key, "원본 자료에서 식별자 값을 확인하세요.", "error")
                    else:
                        keys[(data["entity_type"], fingerprint(properties[primary_key]))].append(data["id"])
                for property_name, property_definition in definition.get("properties", {}).items():
                    if isinstance(property_definition, dict) and property_definition.get("required") and properties.get(property_name) is None:
                        add(f"required-{property_name}", view, [data["id"]], "필수 속성 누락", property_name, "추측하지 말고 실제 값을 확인하세요.", "error")
            for kind in ("nodes", "edges"):
                for item in graph[kind]:
                    data = item["data"]
                    definition = state["schema"]["entities" if kind == "nodes" else "relations"].get(data.get("entity_type" if kind == "nodes" else "relation_type"), {})
                    properties = data.get("props", {})
                    if kind == "edges":
                        for property_name, property_definition in definition.get("properties", {}).items():
                            if isinstance(property_definition, dict) and property_definition.get("required") and properties.get(property_name) is None:
                                add(f"required-{property_name}", view, [data["id"]], "관계 필수 속성 누락", property_name, "관계의 실제 자료를 확인하세요.", "error")
                    for property_name, value in properties.items():
                        property_definition = definition.get("properties", {}).get(property_name)
                        if property_definition is None:
                            add(f"undeclared-{property_name}", view, [data["id"]], "스키마에 없는 속성", property_name, "T-box 속성 정의를 확인하세요. 미정의 속성은 Cypher 복제본에 포함되지 않습니다.")
                        elif not matches_type(value, property_definition):
                            add(f"type-{property_name}", view, [data["id"]], "속성 타입 불일치", f"{property_name}: expected {property_type(property_definition)}", "원본 데이터 또는 T-box 타입을 정정하세요.", "error")
                        elif value is not None and isinstance(property_definition, dict) and "enum" in property_definition and value not in property_definition["enum"]:
                            add(f"enum-{property_name}", view, [data["id"]], "허용되지 않은 enum 값", property_name, "원본 값과 도메인 상태 정의를 확인하세요.", "error")
            for duplicate_ids in keys.values():
                if len(duplicate_ids) > 1:
                    add("duplicate-key", view, duplicate_ids, "타입 내 식별자 중복", "선언된 primary_key 값이 같습니다.", "동일 인스턴스인지 확인하세요.", "error")
            for relation, definition in state["schema"]["relations"].items():
                cardinality = definition.get("cardinality", "N:M").upper()
                for grouped, restricted in ((targets, cardinality in ("N:1", "M:1", "1:1")), (sources, cardinality in ("1:N", "1:M", "1:1"))):
                    if restricted:
                        for (relation_name, element_id), peers in grouped.items():
                            if relation_name == relation and len(peers) > 1:
                                add(f"cardinality-{relation}", view, [element_id] + sorted(peers), "카디널리티 위반", f"{relation} ({cardinality}): {len(peers)}개 연결", "관계 제약 또는 인스턴스 연결을 확인하세요.", "error")
    findings.sort(key=lambda item: ({"error": 0, "warning": 1, "info": 2}[item["severity"]], item["title"], item["id"]))
    counts = Counter(item["severity"] for item in findings if item["status"] == "open")
    return {"revision": state["revision"], "depth": depth, "findings": findings, "counts": {key: counts[key] for key in ("error", "warning", "info")}, "open_count": sum(counts.values()), "notes": notes, "scope": "구조 휴리스틱 검사입니다. 의미 검증·OWL 추론·SHACL 검증은 수행하지 않습니다."}
