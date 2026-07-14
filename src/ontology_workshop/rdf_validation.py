# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Dependency-free, bounded validation for RDF handoff artifacts.

This module deliberately performs structural validation only. It does not run
SPARQL, evaluate SHACL against an RDF dataset, or claim OWL conformance. The
explicit scope keeps the one-day workshop validation useful without turning it
into a background monitoring or retry system.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from .security import safe_export_dir, safe_export_path


VALIDATION_SCOPE = "static_handoff_validation"

REQUIRED_ARTIFACTS = {
    "ontology_ttl": "ontology.ttl",
    "instances_ttl": "instances.ttl",
    "jsonld": "ontology.jsonld",
    "shacl": "shapes.ttl",
    "sparql": "queries.sparql",
    "mapping": "rdf_mapping.md",
    "neptune_rdf_handoff": "neptune_rdf_handoff.md",
}

LIMITATIONS = [
    "RDF and Turtle are checked structurally without a standards-complete RDF parser.",
    "SPARQL seeds are not executed against an RDF store; result correctness and performance are not verified.",
    "SHACL shapes are not evaluated by a SHACL engine, so this result is not a data conformance claim.",
    "OWL reasoning, entailment, named-graph policy, and production Neptune loading are outside this validation scope.",
]

_ALLOWED_QUERY_FORMS = {"SELECT", "ASK", "CONSTRUCT", "DESCRIBE"}
_SPARQL_UPDATE_TERMS = {
    "ADD", "CLEAR", "COPY", "CREATE", "DELETE", "DROP", "INSERT",
    "LOAD", "MOVE",
}
_XSD_TYPES = {
    "STRING": "xsd:string",
    "INT64": "xsd:integer",
    "DOUBLE": "xsd:decimal",
    "BOOLEAN": "xsd:boolean",
    "DATE": "xsd:date",
    "TIMESTAMP": "xsd:dateTime",
}
_LOCAL_NAME = re.compile(r"[^A-Za-z0-9_\-]")


def validate_bundle(bundle: Mapping[str, str],
                    tbox: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate one already-generated RDF handoff bundle exactly once."""
    checks: list[dict[str, Any]] = []
    contents: dict[str, str] = {}
    artifacts: dict[str, dict[str, Any]] = {}
    tbox = tbox if isinstance(tbox, Mapping) else {}

    for key, filename in REQUIRED_ARTIFACTS.items():
        path = str(bundle.get(key) or "")
        artifact = {"name": filename, "path": path, "status": "fail", "bytes": 0}
        artifacts[key] = artifact
        if not path:
            _check(checks, f"artifact.{key}", "artifacts", "fail",
                   f"Required artifact {filename} is not present in the bundle.", filename)
            continue
        try:
            size = os.path.getsize(path)
            artifact["bytes"] = size
            if not os.path.isfile(path) or size <= 0:
                raise ValueError("file is missing or empty")
            with open(path, encoding="utf-8") as handle:
                contents[key] = handle.read()
            artifact["status"] = "pass"
            _check(checks, f"artifact.{key}", "artifacts", "pass",
                   f"{filename} exists and is non-empty ({size} bytes).", filename)
        except (OSError, UnicodeError, ValueError) as exc:
            artifact["error"] = str(exc)
            _check(checks, f"artifact.{key}", "artifacts", "fail",
                   f"Cannot inspect {filename}: {exc}.", filename)

    _validate_jsonld(contents.get("jsonld"), checks)
    _validate_turtle_artifact(
        "ontology", "ontology.ttl", contents.get("ontology_ttl"),
        ("", "rdf", "rdfs", "owl", "xsd"), checks)
    _validate_turtle_artifact(
        "instances", "instances.ttl", contents.get("instances_ttl"),
        ("", "rdf", "rdfs", "owl", "xsd"), checks)
    _validate_ontology(contents.get("ontology_ttl"), tbox, checks)
    shacl_summary = _validate_shacl(contents.get("shacl"), tbox, checks)
    sparql_summary = _validate_sparql(contents.get("sparql"), checks)

    counts = _counts(checks)
    status = _overall_status(checks)
    bundle_path = _bundle_path(artifacts)
    bundle_digest = _content_fingerprint(contents)
    summary = (
        f"Static RDF handoff validation {status}: "
        f"{counts['passed']} passed, {counts['warnings']} warning(s), "
        f"{counts['failed']} failed."
    )
    return {
        "scope": VALIDATION_SCOPE,
        "status": status,
        "validated_at": _now(),
        "bundle_path": bundle_path,
        "bundle_digest": bundle_digest,
        "summary": summary,
        "counts": counts,
        "artifacts": artifacts,
        "sparql": sparql_summary,
        "shacl": shacl_summary,
        "checks": checks,
        "limitations": list(LIMITATIONS),
    }


def source_fingerprint(tbox: Mapping[str, Any] | None,
                       snapshot: Mapping[str, Any] | None,
                       workflow: Mapping[str, Any] | None,
                       base_iri: str | None = None) -> str:
    """Fingerprint only inputs that affect the generated RDF handoff bundle."""
    workflow = workflow if isinstance(workflow, Mapping) else {}
    payload = {
        "tbox": tbox if isinstance(tbox, Mapping) else {},
        "snapshot": _canonical_snapshot(snapshot),
        "base_iri": base_iri or "",
        "competency_questions": _selected_items(
            workflow.get("competency_questions"),
            ("id", "question", "text", "sparql_candidate")),
        "validation_queries": _selected_items(
            workflow.get("validation_queries"),
            ("id", "question_id", "question", "language", "query")),
        "field_mappings": _selected_items(
            workflow.get("field_mappings"),
            ("id", "source", "source_field", "target", "status")),
        "rdf_decisions": _selected_items(
            workflow.get("rdf_decisions"),
            ("id", "topic", "value", "status", "text")),
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_reports(result: Mapping[str, Any], outdir: str) -> dict[str, str]:
    """Write machine- and human-readable evidence without rerunning validation."""
    directory = safe_export_dir(outdir)
    os.makedirs(directory, exist_ok=True)
    json_path = safe_export_path(os.path.join(directory, "validation_report.json"))
    md_path = safe_export_path(os.path.join(directory, "validation_report.md"))
    payload = dict(result)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
        handle.write("\n")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(render_markdown(payload))
    os.chmod(json_path, 0o600)
    os.chmod(md_path, 0o600)
    return {"validation_json": json_path, "validation_markdown": md_path}


def render_markdown(result: Mapping[str, Any]) -> str:
    counts = result.get("counts") or {}
    lines = [
        "# RDF Handoff Static Validation",
        "",
        f"- Scope: `{result.get('scope', VALIDATION_SCOPE)}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Validated at: {result.get('validated_at', '-')}",
        f"- Bundle: {result.get('bundle_path', '-')}",
        f"- Report copy location: {result.get('report_bundle_path', result.get('bundle_path', '-'))}",
        f"- Bundle digest (SHA-256): `{result.get('bundle_digest', '-')}`",
        f"- Source freshness: {result.get('freshness', 'current at validation time')}",
        "- Execution mode: one user-triggered run; no polling or automatic retry",
        "- SPARQL executed: no",
        "- SHACL engine conformance evaluated: no",
        "",
        (f"Checks: {counts.get('passed', 0)} passed, "
         f"{counts.get('warnings', 0)} warning(s), "
         f"{counts.get('failed', 0)} failed."),
        "",
        "## Checks",
        "",
        "| Check | Category | Status | Message |",
        "| --- | --- | --- | --- |",
    ]
    for item in result.get("checks") or []:
        lines.append(
            "| {id} | {category} | {status} | {message} |".format(
                id=_md(item.get("id", "-")),
                category=_md(item.get("category", "-")),
                status=_md(item.get("status", "-")),
                message=_md(item.get("message", "-")),
            )
        )
    lines += ["", "## Limitations", ""]
    for limitation in result.get("limitations") or LIMITATIONS:
        lines.append(f"- {limitation}")
    return "\n".join(lines).rstrip() + "\n"


def _validate_jsonld(text: str | None, checks: list[dict[str, Any]]) -> None:
    if text is None:
        _check(checks, "jsonld.structure", "jsonld", "fail",
               "ontology.jsonld was unavailable for structural inspection.",
               "ontology.jsonld")
        return
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        _check(checks, "jsonld.structure", "jsonld", "fail",
               f"ontology.jsonld is not valid JSON: {exc}.", "ontology.jsonld")
        return
    if not isinstance(value, dict):
        _check(checks, "jsonld.structure", "jsonld", "fail",
               "JSON-LD root must be an object.", "ontology.jsonld")
        return
    graph = value.get("@graph")
    context = value.get("@context")
    failures = []
    if not isinstance(context, (dict, list, str)):
        failures.append("@context")
    if not isinstance(graph, list):
        failures.append("@graph list")
    if failures:
        _check(checks, "jsonld.structure", "jsonld", "fail",
               "JSON-LD is missing a valid " + " and ".join(failures) + ".",
               "ontology.jsonld")
        return
    _check(checks, "jsonld.structure", "jsonld", "pass",
           f"JSON-LD has @context and an @graph list with {len(graph)} item(s).",
           "ontology.jsonld")


def _validate_turtle_artifact(kind: str, filename: str, text: str | None,
                              prefixes: tuple[str, ...],
                              checks: list[dict[str, Any]]) -> None:
    if text is None:
        _check(checks, f"turtle.{kind}.syntax", "turtle", "fail",
               f"{filename} was unavailable for structural inspection.", filename)
        return
    missing = [prefix or "default" for prefix in prefixes
               if not _has_turtle_prefix(text, prefix)]
    if missing:
        _check(checks, f"turtle.{kind}.prefixes", "turtle", "fail",
               f"{filename} is missing prefix declaration(s): {', '.join(missing)}.",
               filename)
    else:
        _check(checks, f"turtle.{kind}.prefixes", "turtle", "pass",
               f"{filename} declares the required prefixes.", filename)
    syntax_error = _balanced_syntax(text, {"[": "]", "(": ")"})
    if syntax_error:
        _check(checks, f"turtle.{kind}.syntax", "turtle", "fail",
               f"{filename} has unbalanced structural syntax: {syntax_error}.", filename)
    else:
        _check(checks, f"turtle.{kind}.syntax", "turtle", "pass",
               f"{filename} has balanced strings, IRIs, and delimiters.", filename)


def _validate_ontology(text: str | None, tbox: Mapping[str, Any],
                       checks: list[dict[str, Any]]) -> None:
    entities = _mapping(tbox.get("entities"))
    relations = _mapping(tbox.get("relations"))
    if text is None:
        _check(checks, "ontology.tbox", "ontology", "fail",
               "ontology.ttl was unavailable for T-Box comparison.", "ontology.ttl")
        return
    if not entities:
        _check(checks, "ontology.tbox", "ontology", "warning",
               "The current T-Box has no entity classes to compare.", "ontology.ttl")
        return
    missing: list[str] = []
    for name, entity in entities.items():
        cname = _name(name)
        if not re.search(rf"(?m)^:{re.escape(cname)}\s+a\s+owl:Class\b", text):
            missing.append(f"class {name}")
        for prop, datatype in _mapping(
                _mapping(entity).get("properties")).items():
            statements = _rdf_statements(text, _name(prop), "owl:DatatypeProperty")
            expected = _XSD_TYPES.get(str(datatype).upper(), "xsd:string")
            if not any(
                    f"rdfs:domain :{cname}" in statement
                    and f"rdfs:range {expected}" in statement
                    for statement in statements):
                missing.append(f"datatype property {name}.{prop}")
    for name, relation in relations.items():
        relation = _mapping(relation)
        statements = _rdf_statements(text, _name(name), "owl:ObjectProperty")
        expected_domain = f"rdfs:domain :{_name(relation.get('src', 'Thing'))}"
        expected_range = f"rdfs:range :{_name(relation.get('dst', 'Thing'))}"
        if not any(expected_domain in statement and expected_range in statement
                   for statement in statements):
            missing.append(f"object property {name}")
        for prop, datatype in _mapping(relation.get("properties")).items():
            prop_statements = _rdf_statements(
                text, _name(prop), "owl:DatatypeProperty")
            expected = _XSD_TYPES.get(str(datatype).upper(), "xsd:string")
            if not any(
                    f"rdfs:domain :{_name(name)}" in statement
                    and f"rdfs:range {expected}" in statement
                    for statement in prop_statements):
                missing.append(f"relationship datatype property {name}.{prop}")
    if missing:
        _check(checks, "ontology.tbox", "ontology", "fail",
               "T-Box declarations missing or inconsistent: " + ", ".join(missing[:12]) + ".",
               "ontology.ttl", {"missing": missing})
    else:
        _check(checks, "ontology.tbox", "ontology", "pass",
               (f"Ontology declarations match {len(entities)} class(es) and "
                f"{len(relations)} relationship type(s) in the T-Box."),
               "ontology.ttl")


def _validate_shacl(text: str | None, tbox: Mapping[str, Any],
                    checks: list[dict[str, Any]]) -> dict[str, Any]:
    entities = _mapping(tbox.get("entities"))
    relations = _mapping(tbox.get("relations"))
    expected_shapes = len(entities) + len(relations)
    if text is None:
        _check(checks, "shacl.syntax", "shacl", "fail",
               "shapes.ttl was unavailable for structural inspection.", "shapes.ttl")
        return {"status": "fail", "shape_count": 0,
                "engine_executed": False, "conforms": None}

    _validate_turtle_artifact(
        "shacl", "shapes.ttl", text, ("", "sh", "xsd"), checks)
    if not entities:
        _check(checks, "shacl.tbox", "shacl", "warning",
               "The current T-Box has no classes, so no class shapes were expected.",
               "shapes.ttl")
    else:
        missing: list[str] = []
        for name, entity in entities.items():
            entity = _mapping(entity)
            cname = _name(name)
            block = _shape_block(text, f"{cname}Shape")
            if not block or f"sh:targetClass :{cname}" not in block:
                missing.append(f"class shape {name}")
                continue
            property_blocks = re.findall(r"sh:property\s*\[(.*?)\]", block, re.DOTALL)
            for prop, datatype in _mapping(entity.get("properties")).items():
                pname = _name(prop)
                prop_block = next(
                    (part for part in property_blocks
                     if re.search(rf"sh:path\s+:{re.escape(pname)}\b", part)), None)
                expected = _XSD_TYPES.get(str(datatype).upper(), "xsd:string")
                if not prop_block or not re.search(
                        rf"sh:datatype\s+{re.escape(expected)}\b", prop_block):
                    missing.append(f"datatype shape {name}.{prop}")
                    continue
                if prop == entity.get("primary_key"):
                    if (not re.search(r"sh:minCount\s+1\b", prop_block)
                            or not re.search(r"sh:maxCount\s+1\b", prop_block)):
                        missing.append(f"primary-key cardinality {name}.{prop}")

        for name, relation in relations.items():
            relation = _mapping(relation)
            pname = _name(name)
            block = _shape_block(text, f"{pname}DomainShape")
            expected = (
                f"sh:targetClass :{_name(relation.get('src', 'Thing'))}",
                f"sh:path :{pname}",
                f"sh:class :{_name(relation.get('dst', 'Thing'))}",
            )
            if not block or any(value not in block for value in expected):
                missing.append(f"relationship shape {name}")

        if missing:
            _check(checks, "shacl.tbox", "shacl", "fail",
                   "SHACL seeds missing or inconsistent with the T-Box: "
                   + ", ".join(missing[:12]) + ".",
                   "shapes.ttl", {"missing": missing})
        else:
            _check(checks, "shacl.tbox", "shacl", "pass",
                   (f"SHACL seeds cover {len(entities)} class shape(s) and "
                    f"{len(relations)} relationship shape(s)."),
                   "shapes.ttl")
    status = _category_status(checks, "shacl")
    return {
        "status": status,
        "shape_count": expected_shapes,
        "engine_executed": False,
        "conforms": None,
    }


def _validate_sparql(text: str | None,
                     checks: list[dict[str, Any]]) -> dict[str, Any]:
    if text is None:
        _check(checks, "sparql.structure", "sparql", "fail",
               "queries.sparql was unavailable for structural inspection.",
               "queries.sparql")
        return {"status": "fail", "query_count": 0, "forms": {},
                "executed": False}
    masked, mask_error = _mask_syntax(text)
    syntax_error = mask_error or _brace_error(masked)
    if syntax_error:
        _check(checks, "sparql.structure", "sparql", "fail",
               f"queries.sparql has unbalanced structural syntax: {syntax_error}.",
               "queries.sparql")
    else:
        _check(checks, "sparql.structure", "sparql", "pass",
               "SPARQL strings, IRIs, and graph-pattern braces are balanced.",
               "queries.sparql")

    top_level = _top_level_text(masked)
    updates = sorted({term for term in _SPARQL_UPDATE_TERMS
                      if re.search(rf"\b{term}\b", top_level, re.IGNORECASE)})
    if updates:
        _check(checks, "sparql.read_only", "sparql", "fail",
               "SPARQL Update operation(s) are not allowed in handoff seeds: "
               + ", ".join(updates) + ".", "queries.sparql")
    else:
        _check(checks, "sparql.read_only", "sparql", "pass",
               "No SPARQL Update operations were detected.", "queries.sparql")

    forms = [value.upper() for value in re.findall(
        r"(?im)^\s*(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", top_level)]
    form_counts = {form: forms.count(form) for form in sorted(set(forms))}
    top_level_words = {value.upper() for value in re.findall(
        r"(?im)^\s*([A-Z]+)\b", top_level)}
    unsupported = sorted(top_level_words - (
            _ALLOWED_QUERY_FORMS
            | _SPARQL_UPDATE_TERMS
            | {"BASE", "PREFIX", "WHERE", "FROM", "NAMED", "ORDER", "GROUP",
               "HAVING", "LIMIT", "OFFSET", "VALUES", "BINDINGS", "WITH", "USING"}
        ))
    if unsupported:
        _check(checks, "sparql.forms", "sparql", "fail",
               "Unsupported top-level SPARQL statement(s): "
               + ", ".join(unsupported) + ".", "queries.sparql")
    elif not forms:
        _check(checks, "sparql.forms", "sparql", "warning",
               "No read-only SPARQL query seeds were found.", "queries.sparql")
    else:
        _check(checks, "sparql.forms", "sparql", "pass",
               (f"Found {len(forms)} read-only query seed(s) using only "
                "SELECT, ASK, CONSTRUCT, or DESCRIBE forms."),
               "queries.sparql", {"forms": form_counts})
    return {
        "status": _category_status(checks, "sparql"),
        "query_count": len(forms),
        "forms": form_counts,
        "executed": False,
    }


def _check(checks: list[dict[str, Any]], check_id: str, category: str,
           status: str, message: str, artifact: str | None = None,
           details: Mapping[str, Any] | None = None) -> None:
    item: dict[str, Any] = {
        "id": check_id,
        "category": category,
        "status": status,
        "message": message,
    }
    if artifact:
        item["artifact"] = artifact
    if details:
        item["details"] = dict(details)
    checks.append(item)


def _counts(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(checks),
        "passed": sum(item.get("status") == "pass" for item in checks),
        "warnings": sum(item.get("status") == "warning" for item in checks),
        "failed": sum(item.get("status") == "fail" for item in checks),
    }


def _overall_status(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "warning"
    if any(item.get("status") == "fail" for item in checks):
        return "fail"
    if any(item.get("status") == "warning" for item in checks):
        return "warning"
    return "pass"


def _category_status(checks: list[dict[str, Any]], category: str) -> str:
    selected = [item for item in checks if item.get("category") == category]
    return _overall_status(selected) if selected else "warning"


def _mapping(value: Any) -> dict:
    return dict(value) if isinstance(value, Mapping) else {}


def _selected_items(value: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    selected = [
        {field: item.get(field) for field in fields if field in item}
        for item in value if isinstance(item, Mapping)
    ]
    return sorted(selected, key=_canonical_json)


def _canonical_snapshot(value: Any) -> dict[str, list[Any]]:
    snapshot = value if isinstance(value, Mapping) else {}
    nodes = snapshot.get("nodes")
    edges = snapshot.get("edges")
    return {
        "nodes": sorted(
            list(nodes) if isinstance(nodes, (list, tuple)) else [],
            key=_canonical_json),
        "edges": sorted(
            list(edges) if isinstance(edges, (list, tuple)) else [],
            key=_canonical_json),
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        default=str)


def _name(value: Any) -> str:
    raw = str(value or "Thing")
    if ":" in raw:
        raw = raw.split(":", 1)[-1]
    raw = _LOCAL_NAME.sub("_", raw).strip("_-") or "Thing"
    return "_" + raw if raw[0].isdigit() else raw


def _rdf_statements(text: str, subject: str, rdf_type: str) -> list[str]:
    return [match.group(0) for match in re.finditer(
        rf"(?ms)^:{re.escape(subject)}\s+a\s+{re.escape(rdf_type)}\s*;(.*?\.)\s*$",
        text,
    )]


def _shape_block(text: str, subject: str) -> str | None:
    match = re.search(
        rf"(?ms)^:{re.escape(subject)}\s+a\s+sh:NodeShape\b(.*?)(?=^\s*$|\Z)",
        text,
    )
    return match.group(0) if match else None


def _has_turtle_prefix(text: str, prefix: str) -> bool:
    marker = re.escape(prefix) + ":" if prefix else ":"
    return bool(re.search(rf"(?m)^\s*@prefix\s+{marker}\s*<[^>]+>\s*\.\s*$", text))


def _balanced_syntax(text: str, pairs: Mapping[str, str]) -> str | None:
    masked, error = _mask_syntax(text)
    if error:
        return error
    stack: list[str] = []
    closing = {value: key for key, value in pairs.items()}
    for char in masked:
        if char in pairs:
            stack.append(char)
        elif char in closing:
            if not stack or stack[-1] != closing[char]:
                return f"unexpected {char}"
            stack.pop()
    return f"unclosed {stack[-1]}" if stack else None


def _mask_syntax(text: str) -> tuple[str, str | None]:
    """Mask comments, quoted strings, and IRIs while preserving line layout."""
    out: list[str] = []
    state = "normal"
    quote = ""
    escaped = False
    for char in text:
        if state == "comment":
            if char == "\n":
                state = "normal"
                out.append("\n")
            else:
                out.append(" ")
            continue
        if state == "iri":
            if char == ">":
                state = "normal"
            out.append("\n" if char == "\n" else " ")
            continue
        if state == "quote":
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                state = "normal"
            out.append("\n" if char == "\n" else " ")
            continue
        if char == "#":
            state = "comment"
            out.append(" ")
        elif char == "<":
            state = "iri"
            out.append(" ")
        elif char in {"'", '"'}:
            state = "quote"
            quote = char
            out.append(" ")
        else:
            out.append(char)
    if state == "quote":
        return "".join(out), "unclosed quoted string"
    if state == "iri":
        return "".join(out), "unclosed IRI"
    return "".join(out), None


def _brace_error(masked: str) -> str | None:
    depth = 0
    for char in masked:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return "unexpected }"
    return "unclosed {" if depth else None


def _top_level_text(masked: str) -> str:
    """Keep text outside graph-pattern braces for operation/form inspection."""
    out: list[str] = []
    depth = 0
    for char in masked:
        if char == "{":
            depth += 1
            out.append(" ")
        elif char == "}":
            depth = max(0, depth - 1)
            out.append(" ")
        elif depth:
            out.append("\n" if char == "\n" else " ")
        else:
            out.append(char)
    return "".join(out)


def _bundle_path(artifacts: Mapping[str, Mapping[str, Any]]) -> str:
    paths = [str(item.get("path")) for item in artifacts.values() if item.get("path")]
    if not paths:
        return ""
    try:
        return str(Path(os.path.commonpath(paths)).resolve())
    except ValueError:
        return str(Path(paths[0]).resolve().parent)


def _content_fingerprint(contents: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for key in REQUIRED_ARTIFACTS:
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(contents.get(key, "")).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _md(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
