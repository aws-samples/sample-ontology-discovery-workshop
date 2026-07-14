# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""RDF/SHACL export for OntoForge AI-ODLC workshops.

This exporter intentionally avoids a runtime RDF dependency. It produces
standards-oriented Turtle, JSON-LD, SHACL, and SPARQL seed artifacts from the
current Kuzu-backed property graph and AI-ODLC workflow state.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from .graph import OntologyGraph
from .security import audit_log, safe_export_dir, safe_export_path, validate_identifier


DEFAULT_BASE_IRI = "https://example.com/ontoforge/"

_NCNAME = re.compile(r"[^A-Za-z0-9_\-]")


def export_all(g: OntologyGraph, outdir: str = "./exports/rdf",
               workflow: dict | None = None,
               base_iri: str = DEFAULT_BASE_IRI) -> dict:
    outdir = safe_export_dir(outdir)
    os.makedirs(outdir, exist_ok=True)
    base_iri = _base(base_iri)
    result = {
        "ontology_ttl": export_ontology_ttl(
            g, os.path.join(outdir, "ontology.ttl"), base_iri),
        "instances_ttl": export_instances_ttl(
            g, os.path.join(outdir, "instances.ttl"), base_iri),
        "jsonld": export_jsonld(
            g, os.path.join(outdir, "ontology.jsonld"), base_iri),
        "shacl": export_shacl(
            g, os.path.join(outdir, "shapes.ttl"), base_iri),
        "sparql": export_sparql_queries(
            g, workflow or {}, os.path.join(outdir, "queries.sparql"), base_iri),
        "mapping": export_mapping_md(
            g, workflow or {}, os.path.join(outdir, "rdf_mapping.md"), base_iri),
        "neptune_rdf_handoff": export_neptune_rdf_handoff_md(
            g, workflow or {}, os.path.join(outdir, "neptune_rdf_handoff.md"), base_iri),
    }
    audit_log("rdf_bundle_exported", outdir=outdir, base_iri=base_iri)
    return result


def export_ontology_ttl(g: OntologyGraph, path: str,
                        base_iri: str = DEFAULT_BASE_IRI) -> str:
    path = safe_export_path(path)
    base_iri = _base(base_iri)
    tb = g.tbox()
    lines = _prefixes(base_iri)
    lines += ["", "# Classes"]
    for name, et in tb.get("entities", {}).items():
        cname = _name(name)
        lines += [
            f":{cname} a owl:Class ;",
            f'  rdfs:label "{_lit(name)}" .',
            "",
        ]
        for prop, typ in et.get("properties", {}).items():
            lines += _datatype_property(prop, cname, typ)

    lines.append("# Object properties")
    for name, rt in tb.get("relations", {}).items():
        pname = _name(name)
        lines += [
            f":{pname} a owl:ObjectProperty ;",
            f'  rdfs:label "{_lit(name)}" ;',
            f"  rdfs:domain :{_name(rt.get('src', 'Thing'))} ;",
            f"  rdfs:range :{_name(rt.get('dst', 'Thing'))} .",
            "",
        ]
        for prop, typ in rt.get("properties", {}).items():
            lines += _datatype_property(prop, pname, typ)

    _write(path, "\n".join(lines).rstrip() + "\n")
    audit_log("rdf_ontology_exported", path=path)
    return path


def export_instances_ttl(g: OntologyGraph, path: str,
                         base_iri: str = DEFAULT_BASE_IRI) -> str:
    path = safe_export_path(path)
    base_iri = _base(base_iri)
    lines = _prefixes(base_iri)
    snap = g.snapshot()
    lines += ["", "# Individuals"]
    for node in snap.get("nodes", []):
        d = node.get("data", {})
        subj = _node_ref(d.get("id", "node"))
        props = d.get("props", {})
        lines.append(f":{subj} a :{_name(d.get('etype', 'Thing'))} ;")
        pred_lines = [
            f"  :{_name(k)} {_ttl_value(v)}"
            for k, v in props.items()
        ]
        if pred_lines:
            lines.append(" ;\n".join(pred_lines) + " .")
        else:
            lines[-1] = lines[-1].rstrip(" ;") + " ."
        lines.append("")

    lines.append("# Relationships")
    for edge in snap.get("edges", []):
        d = edge.get("data", {})
        src = _node_ref(d.get("source", "src"))
        dst = _node_ref(d.get("target", "dst"))
        pred = _name(d.get("label", "RELATED_TO"))
        lines.append(f":{src} :{pred} :{dst} .")
        props = d.get("props") or {}
        if props:
            edge_id = _name(d.get("id", f"{src}-{pred}-{dst}"))
            lines.append(f":{edge_id} a :{pred}Statement ;")
            lines.append(f"  :source :{src} ;")
            lines.append(f"  :target :{dst} ;")
            prop_lines = [f"  :{_name(k)} {_ttl_value(v)}" for k, v in props.items()]
            lines.append(" ;\n".join(prop_lines) + " .")
        lines.append("")

    _write(path, "\n".join(lines).rstrip() + "\n")
    audit_log("rdf_instances_exported", path=path,
              nodes=len(snap.get("nodes", [])), edges=len(snap.get("edges", [])))
    return path


def export_jsonld(g: OntologyGraph, path: str,
                  base_iri: str = DEFAULT_BASE_IRI) -> str:
    path = safe_export_path(path)
    base_iri = _base(base_iri)
    snap = g.snapshot()
    graph: list[dict[str, Any]] = []
    for node in snap.get("nodes", []):
        d = node.get("data", {})
        item = {
            "@id": base_iri + _node_ref(d.get("id", "node")),
            "@type": _name(d.get("etype", "Thing")),
            **{_name(k): v for k, v in (d.get("props") or {}).items()},
        }
        graph.append(item)
    for edge in snap.get("edges", []):
        d = edge.get("data", {})
        graph.append({
            "@id": base_iri + _name(d.get("id", "edge")),
            "@type": _name(d.get("label", "Relationship")),
            "source": {"@id": base_iri + _node_ref(d.get("source", "src"))},
            "target": {"@id": base_iri + _node_ref(d.get("target", "dst"))},
            **{_name(k): v for k, v in (d.get("props") or {}).items()},
        })
    payload = {
        "@context": {
            "@vocab": base_iri,
            "source": {"@type": "@id"},
            "target": {"@type": "@id"},
        },
        "@graph": graph,
    }
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    audit_log("rdf_jsonld_exported", path=path, items=len(graph))
    return path


def export_shacl(g: OntologyGraph, path: str,
                 base_iri: str = DEFAULT_BASE_IRI) -> str:
    path = safe_export_path(path)
    base_iri = _base(base_iri)
    tb = g.tbox()
    lines = _prefixes(base_iri)
    lines += ["", "# Node shapes"]
    for name, et in tb.get("entities", {}).items():
        cname = _name(name)
        lines += [
            f":{cname}Shape a sh:NodeShape ;",
            f"  sh:targetClass :{cname} ;",
        ]
        props = et.get("properties", {}) or {}
        pk = et.get("primary_key", "name")
        blocks = []
        for prop, typ in props.items():
            parts = [
                "    sh:path :" + _name(prop),
                "    sh:datatype " + _xsd(typ),
            ]
            if prop == pk:
                parts.append("    sh:minCount 1")
                parts.append("    sh:maxCount 1")
            blocks.append("  sh:property [\n" + " ;\n".join(parts) + "\n  ]")
        if blocks:
            lines.append(" ;\n".join(blocks) + " .")
        else:
            lines[-1] = lines[-1].rstrip(" ;") + " ."
        lines.append("")

    lines.append("# Relationship shapes")
    for name, rt in tb.get("relations", {}).items():
        pname = _name(name)
        src = _name(rt.get("src", "Thing"))
        dst = _name(rt.get("dst", "Thing"))
        lines += [
            f":{pname}DomainShape a sh:NodeShape ;",
            f"  sh:targetClass :{src} ;",
            "  sh:property [",
            f"    sh:path :{pname} ;",
            f"    sh:class :{dst}",
            "  ] .",
            "",
        ]

    _write(path, "\n".join(lines).rstrip() + "\n")
    audit_log("rdf_shacl_exported", path=path)
    return path


def export_sparql_queries(g: OntologyGraph, workflow: dict,
                          path: str,
                          base_iri: str = DEFAULT_BASE_IRI) -> str:
    path = safe_export_path(path)
    base_iri = _base(base_iri)
    tb = g.tbox()
    lines = [
        f"PREFIX : <{base_iri}>",
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
        "",
        "# Seed SPARQL queries generated from the current ontology.",
        "",
    ]
    for name in tb.get("entities", {}):
        cname = _name(name)
        lines += [
            f"# List instances of {name}",
            f"SELECT ?s WHERE {{ ?s a :{cname} . }} LIMIT 25",
            "",
        ]
    for q in workflow.get("competency_questions") or []:
        question = q.get("question") or q.get("text")
        if question:
            sparql = q.get("sparql_candidate")
            lines += [
                "# Competency question",
                "# " + str(question).replace("\n", " "),
                "# TODO: refine this query during SPARQL validation.",
                sparql or "SELECT * WHERE { ?s ?p ?o . } LIMIT 25",
                "",
            ]
    for item in workflow.get("validation_queries") or []:
        if str(item.get("language", "")).lower() != "sparql":
            continue
        query = item.get("query")
        if not query:
            continue
        lines += [
            "# Workflow SPARQL seed",
            "# " + str(item.get("question") or item.get("question_id") or "").replace("\n", " "),
            str(query),
            "",
        ]
    _write(path, "\n".join(lines).rstrip() + "\n")
    audit_log("rdf_sparql_exported", path=path)
    return path


def export_mapping_md(g: OntologyGraph, workflow: dict,
                      path: str,
                      base_iri: str = DEFAULT_BASE_IRI) -> str:
    path = safe_export_path(path)
    base_iri = _base(base_iri)
    tb = g.tbox()
    lines = [
        "# RDF Mapping",
        "",
        f"- Base IRI: {base_iri}",
        "- URI rule: graph element identifiers are slugged under the base IRI.",
        "- Labels: source graph labels are preserved as literal values.",
        "",
        "## Classes",
        "",
        "| Entity | RDF class | Primary key |",
        "| --- | --- | --- |",
    ]
    for name, et in tb.get("entities", {}).items():
        lines.append(f"| {name} | :{_name(name)} | {et.get('primary_key', 'name')} |")
    lines += ["", "## Object Properties", "",
              "| Relation | Domain | Range |",
              "| --- | --- | --- |"]
    for name, rt in tb.get("relations", {}).items():
        lines.append(
            f"| {name} | :{_name(rt.get('src', 'Thing'))} | "
            f":{_name(rt.get('dst', 'Thing'))} |"
        )
    mappings = workflow.get("field_mappings") or []
    if mappings:
        lines += ["", "## Source Field Mappings", "",
                  "| Source | Field | Target | Status |",
                  "| --- | --- | --- | --- |"]
        for m in mappings:
            lines.append(
                f"| {m.get('source', '-')} | {m.get('source_field', '-')} | "
                f"{m.get('target', '-')} | {m.get('status', '-')} |"
            )
    rdf_decisions = workflow.get("rdf_decisions") or []
    if rdf_decisions:
        lines += ["", "## RDF Decisions Captured in Workflow", "",
                  "| Topic | Value | Status | Note |",
                  "| --- | --- | --- | --- |"]
        for item in rdf_decisions:
            lines.append(
                f"| {item.get('topic', '-')} | {item.get('value', '-')} | "
                f"{item.get('status', '-')} | {item.get('text', '-')} |"
            )
    _write(path, "\n".join(lines).rstrip() + "\n")
    audit_log("rdf_mapping_exported", path=path)
    return path


def export_neptune_rdf_handoff_md(g: OntologyGraph, workflow: dict,
                                  path: str,
                                  base_iri: str = DEFAULT_BASE_IRI) -> str:
    path = safe_export_path(path)
    base_iri = _base(base_iri)
    tb = g.tbox()
    lines = [
        "# Neptune RDF Handoff Notes",
        "",
        f"- Base IRI: {base_iri}",
        "- Target: Amazon Neptune RDF/SPARQL follow-up, not a completed production load plan.",
        "- Validate URI generation, named graph strategy, IAM/network posture, loader source S3 layout, and SHACL policy before production use.",
        "",
        "## Current RDF Export Bundle",
        "",
        "- ontology.ttl: class/property skeleton from the current T-Box.",
        "- instances.ttl: current A-Box individuals and relationship triples.",
        "- ontology.jsonld: exchange form for downstream RDF tooling.",
        "- shapes.ttl: seed SHACL constraints for datatype/key checks.",
        "- queries.sparql: seed SPARQL queries requiring execution validation.",
        "",
        "## Neptune Follow-up Checklist",
        "",
        "- Confirm base IRI and URI stability rules with data owners.",
        "- Decide whether workshop/source/system partitions require named graphs.",
        "- Convert seed SHACL shapes into enforceable validation gates.",
        "- Run SPARQL candidates against a representative Neptune or RDF test store.",
        "- Decide whether property graph openCypher and RDF/SPARQL exports remain dual deliverables.",
        "",
        "## Model Size Snapshot",
        "",
        f"- Classes: {len(tb.get('entities', {}))}",
        f"- Object properties: {len(tb.get('relations', {}))}",
    ]
    decisions = workflow.get("rdf_decisions") or []
    if decisions:
        lines += ["", "## Captured RDF Decisions", "", "| Topic | Value | Status |", "| --- | --- | --- |"]
        for item in decisions:
            lines.append(f"| {item.get('topic', '-')} | {item.get('value', item.get('text', '-'))} | {item.get('status', '-')} |")
    queries = [q for q in workflow.get("validation_queries") or [] if str(q.get("language", "")).lower() == "sparql"]
    if queries:
        lines += ["", "## SPARQL Seed Readiness", ""]
        for q in queries[:8]:
            lines.append(f"- {q.get('question') or q.get('question_id') or 'question'}: {q.get('readiness', 'seed_only')}")
    _write(path, "\n".join(lines).rstrip() + "\n")
    audit_log("neptune_rdf_handoff_exported", path=path)
    return path


def _prefixes(base_iri: str) -> list[str]:
    return [
        f"@base <{base_iri}> .",
        f"@prefix : <{base_iri}> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix sh: <http://www.w3.org/ns/shacl#> .",
    ]


def _datatype_property(prop: str, domain: str, typ: str) -> list[str]:
    pname = _name(prop)
    return [
        f":{pname} a owl:DatatypeProperty ;",
        f'  rdfs:label "{_lit(prop)}" ;',
        f"  rdfs:domain :{domain} ;",
        f"  rdfs:range {_xsd(typ)} .",
        "",
    ]


def _base(value: str | None) -> str:
    value = (value or DEFAULT_BASE_IRI).strip()
    if not (value.startswith("http://") or value.startswith("https://")):
        raise ValueError("base IRI must start with http:// or https://")
    if not value.endswith(("/", "#")):
        value += "/"
    return value


def _name(value: Any) -> str:
    raw = str(value or "Thing")
    if ":" in raw:
        raw = raw.split(":", 1)[-1]
    raw = _NCNAME.sub("_", raw).strip("_-")
    if not raw:
        raw = "Thing"
    if raw[0].isdigit():
        raw = "_" + raw
    try:
        validate_identifier(raw.replace("-", "_"), "RDF local name")
    except ValueError:
        pass
    return raw


def _node_ref(node_id: Any) -> str:
    text = str(node_id or "node")
    if ":" in text:
        etype, key = text.split(":", 1)
        return _name(etype) + "/" + _name(key)
    return _name(text)


def _ttl_value(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return f'"{str(value).lower()}"^^xsd:boolean'
    if isinstance(value, int) and not isinstance(value, bool):
        return f'"{value}"^^xsd:integer'
    if isinstance(value, float):
        return f'"{value}"^^xsd:decimal'
    return f'"{_lit(value)}"'


def _xsd(kuzu_type: str | None) -> str:
    mapping = {
        "STRING": "xsd:string",
        "INT64": "xsd:integer",
        "DOUBLE": "xsd:decimal",
        "BOOLEAN": "xsd:boolean",
        "DATE": "xsd:date",
        "TIMESTAMP": "xsd:dateTime",
    }
    return mapping.get(str(kuzu_type or "STRING").upper(), "xsd:string")


def _lit(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\"')


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(path, 0o600)
