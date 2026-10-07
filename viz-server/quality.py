from __future__ import annotations

from collections import Counter, defaultdict
from difflib import SequenceMatcher
import datetime
import math

from model import fingerprint, property_type


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
