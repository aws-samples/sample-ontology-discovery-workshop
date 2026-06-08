# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
OntoForge — graph engine
Kùzu(임베디드 property graph)를 단일 진실원천으로 사용.
T-Box(스키마)와 A-Box(인스턴스)를 개념적으로 분리해 관리한다.
"""
from __future__ import annotations
import os
import shutil
from dataclasses import dataclass, field, asdict
from typing import Any

import kuzu

from .security import (
    MAX_ROWS,
    KUZU_TYPES,
    audit_log,
    validate_identifier,
    validate_property_schema,
    validate_readonly_cypher,
    validate_type,
)


@dataclass
class EntityType:
    """T-Box: 노드 타입 정의"""
    name: str
    properties: dict[str, str] = field(default_factory=dict)  # propname -> kuzu type
    primary_key: str = "name"


@dataclass
class RelationType:
    """T-Box: 관계 타입 정의"""
    name: str
    src: str
    dst: str
    cardinality: str = "N:M"  # 문서용 메타
    properties: dict[str, str] = field(default_factory=dict)


class OntologyGraph:
    """워크샵 동안 점진적으로 진화하는 온톨로지 그래프."""

    KUZU_TYPES = KUZU_TYPES

    def __init__(self, db_path: str = "./workshop.kuzu", fresh: bool = False):
        self.db_path = db_path
        if fresh:
            for p in (db_path, db_path + ".wal"):
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                elif os.path.exists(p):
                    os.remove(p)
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        # 메타: 도구가 알고 있는 T-Box (Kùzu 카탈로그 + 우리 메타데이터)
        self.entity_types: dict[str, EntityType] = {}
        self.relation_types: dict[str, RelationType] = {}
        if not fresh:
            self._rehydrate()

    def _rehydrate(self) -> None:
        """기존 Kùzu DB(재시작)에서 T-Box 레지스트리를 카탈로그로 복원.
        서버 재시작 후에도 스키마/인스턴스가 그대로 살아있도록 한다."""
        def _rows(q):
            try:
                r = self.conn.execute(q)
            except Exception:  # noqa: BLE001
                return []
            out = []
            while r.has_next():
                out.append(r.get_next())
            return out

        tables = _rows("CALL show_tables() RETURN *")  # [id, name, type, db, comment]
        for row in tables:
            name, ttype = row[1], row[2]
            try:
                name = validate_identifier(name, "Kuzu table name")
            except ValueError:
                continue
            if ttype == "NODE":
                cols = _rows(f"CALL table_info('{name}') RETURN *")
                props, pk = {}, "name"
                for c in cols:  # [property id, name, type, default, primary key]
                    cname, ctype, is_pk = c[1], c[2], c[4]
                    if is_pk:
                        pk = cname
                    else:
                        props[cname] = ctype
                self.entity_types[name] = EntityType(name=name, properties=props,
                                                     primary_key=pk)
        for row in tables:
            name, ttype = row[1], row[2]
            try:
                name = validate_identifier(name, "Kuzu table name")
            except ValueError:
                continue
            if ttype == "REL":
                conn_rows = _rows(f"CALL show_connection('{name}') RETURN *")
                if not conn_rows:
                    continue
                src, dst = conn_rows[0][0], conn_rows[0][1]
                cols = _rows(f"CALL table_info('{name}') RETURN *")
                props = {c[1]: c[2] for c in cols}
                self.relation_types[name] = RelationType(
                    name=name, src=src, dst=dst, properties=props)

    # ---- T-Box 조작 -------------------------------------------------
    def add_entity_type(self, et: EntityType) -> dict:
        try:
            name = validate_identifier(et.name, "entity type")
            pk = validate_identifier(et.primary_key, "primary key")
            stored_props = validate_property_schema(et.properties)
            ddl_props = dict(stored_props)
            if pk not in ddl_props:
                ddl_props[pk] = "STRING"
            if name in self.entity_types:
                return {"ok": True, "noop": True, "entity": name}
            cols = ", ".join(f"{k} {self._vt(v)}" for k, v in ddl_props.items())
            ddl = f"CREATE NODE TABLE {name}({cols}, PRIMARY KEY({pk}))"
            self.conn.execute(ddl)  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
            self.entity_types[name] = EntityType(name, stored_props, pk)
            audit_log("entity_type_added", entity=name, properties=list(stored_props))
            return {"ok": True, "ddl": ddl, "entity": name}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def add_relation_type(self, rt: RelationType) -> dict:
        try:
            name = validate_identifier(rt.name, "relation type")
            src = validate_identifier(rt.src, "source entity type")
            dst = validate_identifier(rt.dst, "destination entity type")
            props = validate_property_schema(rt.properties)
            if src not in self.entity_types:
                raise ValueError(f"unknown source entity type {src}")
            if dst not in self.entity_types:
                raise ValueError(f"unknown destination entity type {dst}")
            if name in self.relation_types:
                return {"ok": True, "noop": True, "relation": name}
            extra = ""
            if props:
                extra = ", " + ", ".join(f"{k} {self._vt(v)}" for k, v in props.items())
            ddl = f"CREATE REL TABLE {name}(FROM {src} TO {dst}{extra})"
            self.conn.execute(ddl)  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
            self.relation_types[name] = RelationType(
                name, src, dst, rt.cardinality, props)
            audit_log("relation_type_added", relation=name, src=src, dst=dst)
            return {"ok": True, "ddl": ddl, "relation": name}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    # ---- A-Box 조작 -------------------------------------------------
    @staticmethod
    def _param_ref(key: str, kuzu_type: str) -> str:
        # Kùzu는 STRING 파라미터를 DATE/TIMESTAMP로 암시적 캐스트하지 않으므로 명시 캐스트
        if kuzu_type == "DATE":
            return f"date(${key})"
        if kuzu_type == "TIMESTAMP":
            return f"timestamp(${key})"
        return f"${key}"

    def add_instance(self, etype: str, props: dict[str, Any]) -> dict:
        try:
            etype = validate_identifier(etype, "entity type")
            if etype not in self.entity_types:
                return {"ok": False, "error": f"unknown entity type {etype}"}
            et = self.entity_types[etype]
            ptypes = dict(et.properties)
            ptypes.setdefault(et.primary_key, "STRING")
            cleaned: dict[str, Any] = {}
            for k, v in props.items():
                prop = validate_identifier(k, "property name")
                if prop not in ptypes:
                    raise ValueError(f"unknown property {etype}.{prop}")
                cleaned[prop] = v
            keys = ", ".join(
                f"{k}: {self._param_ref(k, ptypes.get(k, 'STRING'))}" for k in cleaned)
            self.conn.execute(  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
                f"MERGE (n:{etype} {{{keys}}})", parameters=cleaned)
            audit_log("instance_upserted", entity=etype, key=cleaned.get(et.primary_key))
            return {"ok": True, "etype": etype, "props": cleaned}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def add_edge(self, rtype: str, src_key: str, dst_key: str,
                 props: dict[str, Any] | None = None) -> dict:
        try:
            rtype = validate_identifier(rtype, "relation type")
            rt = self.relation_types.get(rtype)
            if not rt:
                return {"ok": False, "error": f"unknown relation type {rtype}"}
            spk = self.entity_types[rt.src].primary_key
            dpk = self.entity_types[rt.dst].primary_key
            props = props or {}
            ptypes = dict(rt.properties or {})
            cleaned: dict[str, Any] = {}
            for k, v in props.items():
                prop = validate_identifier(k, "relationship property name")
                if prop not in ptypes:
                    raise ValueError(f"unknown relationship property {rtype}.{prop}")
                cleaned[prop] = v
            setclause = ""
            if cleaned:
                setclause = " SET " + ", ".join(
                    f"e.{k} = {self._param_ref(k, ptypes.get(k, 'STRING'))}"
                    for k in cleaned)
            cypher = (
                f"MATCH (a:{rt.src} {{{spk}: $src}}), (b:{rt.dst} {{{dpk}: $dst}}) "
                f"MERGE (a)-[e:{rtype}]->(b){setclause}"
            )
            params = {"src": src_key, "dst": dst_key, **cleaned}
            self.conn.execute(cypher, parameters=params)  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
            audit_log("edge_upserted", relation=rtype, src=src_key, dst=dst_key)
            return {"ok": True, "rtype": rtype, "src": src_key, "dst": dst_key}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    # ---- 변경/삭제 (M2: 변경 모드) ----------------------------------
    def delete_instance(self, etype: str, key: str) -> dict:
        try:
            etype = validate_identifier(etype, "entity type")
            if etype not in self.entity_types:
                return {"ok": False, "error": f"unknown entity type {etype}"}
            pk = self.entity_types[etype].primary_key
            self.conn.execute(  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
                f"MATCH (n:{etype} {{{pk}: $k}}) DETACH DELETE n",
                parameters={"k": key})
            audit_log("instance_deleted", entity=etype, key=key)
            return {"ok": True, "deleted": f"{etype}:{key}"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def delete_edge(self, rtype: str, src_key: str, dst_key: str) -> dict:
        try:
            rtype = validate_identifier(rtype, "relation type")
            rt = self.relation_types.get(rtype)
            if not rt:
                return {"ok": False, "error": f"unknown relation type {rtype}"}
            spk = self.entity_types[rt.src].primary_key
            dpk = self.entity_types[rt.dst].primary_key
            self.conn.execute(  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
                f"MATCH (a:{rt.src} {{{spk}: $s}})-[e:{rtype}]->(b:{rt.dst} {{{dpk}: $d}}) "
                f"DELETE e", parameters={"s": src_key, "d": dst_key})
            audit_log("edge_deleted", relation=rtype, src=src_key, dst=dst_key)
            return {"ok": True, "deleted": f"{rtype}:{src_key}->{dst_key}"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def drop_relation_type(self, name: str) -> dict:
        try:
            name = validate_identifier(name, "relation type")
            if name not in self.relation_types:
                return {"ok": False, "error": f"unknown relation type {name}"}
            self.conn.execute(f"DROP TABLE {name}")  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
            self.relation_types.pop(name, None)
            audit_log("relation_type_dropped", relation=name)
            return {"ok": True, "dropped": name}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def drop_entity_type(self, name: str) -> dict:
        try:
            name = validate_identifier(name, "entity type")
            if name not in self.entity_types:
                return {"ok": False, "error": f"unknown entity type {name}"}
            # 의존 관계 테이블 먼저 제거
            deps = [r for r, rt in self.relation_types.items()
                    if rt.src == name or rt.dst == name]
            for r in deps:
                self.drop_relation_type(r)
            self.conn.execute(f"DROP TABLE {name}")  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
            self.entity_types.pop(name, None)
            audit_log("entity_type_dropped", entity=name, dropped_relations=deps)
            return {"ok": True, "dropped": name, "dropped_relations": deps}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def reset(self) -> dict:
        """백지 시작: 모든 관계·엔티티 테이블 제거."""
        for r in list(self.relation_types):
            self.conn.execute(f"DROP TABLE {r}")  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
        for e in list(self.entity_types):
            self.conn.execute(f"DROP TABLE {e}")  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
        self.relation_types.clear()
        self.entity_types.clear()
        audit_log("graph_reset")
        return {"ok": True, "reset": True}

    # ---- 질의 -------------------------------------------------------
    def _readonly_query(self, cypher: str, parameters: dict | None = None,
                        max_rows: int | None = MAX_ROWS,
                        audit: bool = True) -> dict:
        cypher = validate_readonly_cypher(cypher)
        res = self.conn.execute(cypher, parameters=parameters or {})
        cols = res.get_column_names()
        rows = []
        truncated = False
        while res.has_next():
            if max_rows is not None and len(rows) >= max_rows:
                truncated = True
                break
            rows.append(res.get_next())
        if audit:
            audit_log("query_executed", rows=len(rows), truncated=truncated)
        return {"ok": True, "columns": cols, "rows": rows,
                "count": len(rows), "truncated": truncated}

    def query(self, cypher: str, parameters: dict | None = None,
              max_rows: int = MAX_ROWS) -> dict:
        try:
            return self._readonly_query(cypher, parameters, max_rows=max_rows)
        except Exception as e:  # noqa: BLE001 - surface to UI
            return {"ok": False, "error": str(e), "cypher": cypher}

    def _query_all(self, cypher: str, parameters: dict | None = None) -> dict:
        """Internal read path for operational snapshots and exports.

        Public user-submitted queries remain capped by query().
        """
        try:
            return self._readonly_query(
                cypher, parameters, max_rows=None, audit=False)
        except Exception as e:  # noqa: BLE001 - keep snapshot behavior tolerant
            return {"ok": False, "error": str(e), "cypher": cypher}

    # ---- 시각화용 스냅샷 -------------------------------------------
    def snapshot(self) -> dict:
        """현재 A-Box 전체를 Cytoscape elements 형태로 반환."""
        nodes, edges = [], []
        for etype, et in self.entity_types.items():
            r = self._query_all(f"MATCH (n:{etype}) RETURN n")
            for row in r.get("rows", []):
                n = row[0]
                pk = n.get(et.primary_key)
                nid = f"{etype}:{pk}"
                disp = n.get("title") or n.get("name") or pk
                nodes.append({"data": {"id": nid, "label": str(disp),
                                       "etype": etype, "props": _clean(n)}})
        for rtype, rt in self.relation_types.items():
            spk = self.entity_types[rt.src].primary_key
            dpk = self.entity_types[rt.dst].primary_key
            r = self._query_all(
                f"MATCH (a:{rt.src})-[e:{rtype}]->(b:{rt.dst}) "
                f"RETURN a.{spk}, b.{dpk}, e"
            )
            for row in r.get("rows", []):
                s, d, e = row[0], row[1], row[2]
                edges.append({"data": {
                    "id": f"{rtype}:{s}->{d}",
                    "source": f"{rt.src}:{s}", "target": f"{rt.dst}:{d}",
                    "label": rtype, "props": _clean(e or {}),
                }})
        return {"nodes": nodes, "edges": edges}

    def tbox(self) -> dict:
        """스키마(T-Box)를 시각화/문서용으로 반환."""
        return {
            "entities": {k: asdict(v) for k, v in self.entity_types.items()},
            "relations": {k: asdict(v) for k, v in self.relation_types.items()},
        }

    def _vt(self, t: str) -> str:
        return validate_type(t)


def _clean(d: dict) -> dict:
    """Kùzu 내부 키(_id, _label 등) 제거."""
    return {k: v for k, v in d.items() if not k.startswith("_")}
