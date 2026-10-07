from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter


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


def structural_errors(state):
    errors = []
    for view, graph in state["graphs"].items():
        counts = Counter(item["data"]["id"] for kind in graph.values() for item in kind)
        errors.extend(f"{view}: duplicate element id {key}" for key, count in counts.items() if count > 1)
        nodes = {item["data"]["id"]: item["data"] for item in graph["nodes"]}
        for data in nodes.values():
            parent = data.get("parent")
            ancestors = {data["id"]}
            while parent:
                if parent not in nodes:
                    errors.append(f"{view}: missing compound parent for {data['id']}")
                    break
                if parent in ancestors:
                    errors.append(f"{view}: cyclic compound parent for {data['id']}")
                    break
                ancestors.add(parent)
                parent = nodes[parent].get("parent")
        for edge in graph["edges"]:
            data = edge["data"]
            if data["source"] not in nodes or data["target"] not in nodes:
                errors.append(f"{view}: dangling edge {data['id']}")
            if view == "abox":
                definition = state["schema"]["relations"].get(data["relation_type"])
                if not definition:
                    errors.append(f"abox: unknown relation type {data['relation_type']}")
                elif data["source"] in nodes and data["target"] in nodes:
                    if (nodes[data["source"]]["entity_type"], nodes[data["target"]]["entity_type"]) != (definition["src"], definition["dst"]):
                        errors.append(f"abox: endpoint type mismatch for {data['id']}")
        if view == "abox":
            for data in nodes.values():
                if data["entity_type"] not in state["schema"]["entities"]:
                    errors.append(f"abox: unknown entity type {data['entity_type']}")
    return errors


def diff_states(before, after):
    changes = []
    for view in ("tbox", "abox"):
        for kind in ("nodes", "edges"):
            old = {item["data"]["id"]: item["data"] for item in before["graphs"][view][kind]} if before else {}
            new = {item["data"]["id"]: item["data"] for item in after["graphs"][view][kind]}
            for element_id in sorted(old.keys() | new.keys()):
                if old.get(element_id) == new.get(element_id):
                    continue
                operation = "added" if element_id not in old else "removed" if element_id not in new else "updated"
                changes.append({"view": view, "kind": kind, "id": element_id, "operation": operation, "before": old.get(element_id), "after": new.get(element_id)})
    for field in ("metadata", "queries", "quality_decisions"):
        old_value = before.get(field) if before else None
        new_value = after[field]
        if old_value != new_value:
            changes.append({"view": "model", "kind": field, "id": field, "operation": "added" if before is None else "updated", "before": old_value, "after": new_value})
    return changes
