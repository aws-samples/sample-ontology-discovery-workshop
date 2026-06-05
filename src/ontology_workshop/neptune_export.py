# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""합의된 온톨로지를 Amazon Neptune으로 승격하기 위한 익스포트.
①openCypher CREATE 스크립트  ②Neptune Bulk Loader CSV (노드/엣지)
주의: 로컬 openCypher가 Neptune에서 100% 동작을 보장하지는 않는다(PRD §6.4)."""
from __future__ import annotations
import csv
import os
from .graph import OntologyGraph
from .security import audit_log, safe_export_dir, safe_export_path
from .security import validate_identifier


IAM_SECURITY_NOTES = """
Security requirements for loading these exports into Amazon Neptune:
- Use an IAM role assumed by Neptune for Bulk Loader access.
- Scope S3 permissions to the exact export bucket/prefix only:
  s3:ListBucket on arn:aws:s3:::<bucket> with a prefix condition, and
  s3:GetObject on arn:aws:s3:::<bucket>/<prefix>/*.
- Scope data-plane permissions to the target cluster resource:
  neptune-db:StartLoaderJob, neptune-db:GetLoaderJobStatus,
  neptune-db:ReadDataViaQuery, and neptune-db:WriteDataViaQuery on
  arn:aws:neptune-db:<region>:<account>:<cluster-resource-id>/*.
- Keep the S3 bucket and Neptune cluster in the same Region, use SSE-KMS,
  Block Public Access, HTTPS-only bucket policies, VPC endpoints, and private
  subnets to avoid public internet exposure.
"""


def _m(name, schema_map):
    """schema_map(한글 식별자→영문)이 있으면 변환, 없으면 원본. 개발자 적재용 산출물에 사용."""
    return validate_identifier(schema_map.get(name, name) if schema_map else name,
                               "export identifier")


def export_opencypher(g: OntologyGraph, path: str,
                      schema_map: dict | None = None) -> str:
    path = safe_export_path(path)
    snap = g.snapshot()
    lines = []
    for n in snap["nodes"]:
        d = n["data"]
        props = {"_etype": _m(d["etype"], schema_map),
                 **{_m(k, schema_map): v for k, v in d["props"].items()}}
        kv = ", ".join(f"{k}: {_lit(v)}" for k, v in props.items())
        lines.append(f"CREATE (`{d['id']}`:{_m(d['etype'], schema_map)} {{{kv}}})")
    for e in snap["edges"]:
        d = e["data"]
        eprops = {_m(k, schema_map): v for k, v in d["props"].items()}
        kv = ", ".join(f"{k}: {_lit(v)}" for k, v in eprops.items())
        propblock = f" {{{kv}}}" if kv else ""
        lines.append(
            f"MATCH (a {{`~id`: '{d['source']}'}}), (b {{`~id`: '{d['target']}'}}) "
            f"CREATE (a)-[:{_m(d['label'], schema_map)}{propblock}]->(b)"
        )
    text = ";\n".join(lines) + ";\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(path, 0o600)
    audit_log("neptune_opencypher_exported", path=path, nodes=len(snap["nodes"]),
              edges=len(snap["edges"]))
    return path


def export_bulk_csv(g: OntologyGraph, outdir: str,
                    schema_map: dict | None = None) -> dict:
    """Amazon Neptune Gremlin/openCypher bulk loader 포맷 CSV."""
    outdir = safe_export_dir(outdir)
    os.makedirs(outdir, exist_ok=True)
    snap = g.snapshot()
    nodes_path = os.path.join(outdir, "nodes.csv")
    edges_path = os.path.join(outdir, "edges.csv")

    with open(nodes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["~id", "~label", "name:String", "props:String"])
        for n in snap["nodes"]:
            d = n["data"]
            props = {_m(k, schema_map): v for k, v in d["props"].items()}
            w.writerow([d["id"], _m(d["etype"], schema_map), d["label"], str(props)])
    os.chmod(nodes_path, 0o600)

    with open(edges_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["~id", "~from", "~to", "~label", "props:String"])
        for e in snap["edges"]:
            d = e["data"]
            props = {_m(k, schema_map): v for k, v in d["props"].items()}
            w.writerow([d["id"], d["source"], d["target"],
                        _m(d["label"], schema_map), str(props)])
    os.chmod(edges_path, 0o600)

    audit_log("neptune_bulk_csv_exported", outdir=outdir, nodes=len(snap["nodes"]),
              edges=len(snap["edges"]))
    return {"nodes": nodes_path, "edges": edges_path}


def _lit(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "\\'") + "'"
