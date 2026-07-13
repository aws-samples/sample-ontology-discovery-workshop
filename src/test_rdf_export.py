"""RDF/SHACL export smoke checks."""
from __future__ import annotations

import json
import os
import tempfile

from ontology_workshop.graph import EntityType, OntologyGraph, RelationType
from ontology_workshop import rdf_export


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    root = tempfile.mkdtemp(prefix="ontoforge-rdf-")
    db = os.path.join(root, "rdf.kuzu")
    out = "./exports/test_rdf"
    g = OntologyGraph(db, fresh=True)
    assert g.add_entity_type(EntityType(
        "Product", {"id": "STRING", "name": "STRING"}, "id"))["ok"]
    assert g.add_entity_type(EntityType(
        "SupplierLot", {"id": "STRING", "supplier": "STRING"}, "id"))["ok"]
    assert g.add_relation_type(RelationType(
        "USES_LOT", "Product", "SupplierLot", "N:M", {}))["ok"]
    assert g.add_instance("Product", {"id": "P1", "name": "Widget"})["ok"]
    assert g.add_instance("SupplierLot", {"id": "L1", "supplier": "ACME"})["ok"]
    assert g.add_edge("USES_LOT", "P1", "L1", {})["ok"]

    workflow = {
        "competency_questions": [{
            "question": "Which supplier lots are connected to defective products?"
        }],
        "field_mappings": [{
            "source": "quality_inspection",
            "source_field": "product_id",
            "target": "Product.id",
            "status": "available",
        }],
        "rdf_decisions": [{
            "topic": "base_iri",
            "value": "https://example.com/test-ontology/",
            "status": "candidate",
        }],
    }
    result = rdf_export.export_all(
        g, out, workflow, "https://example.com/test-ontology/")
    for key, path in result.items():
        require(os.path.exists(path), f"missing {key}: {path}")

    ontology = open(result["ontology_ttl"], encoding="utf-8").read()
    instances = open(result["instances_ttl"], encoding="utf-8").read()
    shapes = open(result["shacl"], encoding="utf-8").read()
    sparql = open(result["sparql"], encoding="utf-8").read()
    mapping = open(result["mapping"], encoding="utf-8").read()
    handoff = open(result["neptune_rdf_handoff"], encoding="utf-8").read()
    data = json.load(open(result["jsonld"], encoding="utf-8"))

    require(":Product a owl:Class" in ontology, "Product class missing")
    require(":USES_LOT a owl:ObjectProperty" in ontology, "relation property missing")
    require(":Product/P1 a :Product" in instances, "Product individual missing")
    require(":Product/P1 :USES_LOT :SupplierLot/L1" in instances, "edge triple missing")
    require("sh:targetClass :Product" in shapes, "Product SHACL shape missing")
    require("Which supplier lots" in sparql, "competency question missing from SPARQL")
    require("quality_inspection" in mapping, "field mapping missing")
    require("Neptune RDF Handoff" in handoff, "Neptune RDF handoff note missing")
    require("Captured RDF Decisions" in handoff, "RDF decisions missing from handoff")
    require(len(data.get("@graph", [])) == 3, "JSON-LD graph should include two nodes and one edge")
    print("RDF export checks passed")


if __name__ == "__main__":
    main()
