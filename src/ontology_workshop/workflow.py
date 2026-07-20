# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""AI-ODLC workflow state for OntoForge.

The graph remains the source of truth for T-Box/A-Box. This module stores the
workshop lifecycle state around that graph: claims, user stories, competency
questions, data mappings, risks, and gate status.
"""
from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import re
from typing import Any


STAGES = [
    "inception",
    "discovery",
    "event_discovery",
    "story_to_question",
    "model_synthesis",
    "data_grounding",
    "adversarial_review",
    "validation_handoff",
]

STAGE_LABELS = {
    "inception": "Inception",
    "discovery": "Discovery",
    "event_discovery": "Event Discovery",
    "story_to_question": "Story-to-Question Mapping",
    "model_synthesis": "Model Synthesis",
    "data_grounding": "Data Grounding",
    "adversarial_review": "Adversarial Review",
    "validation_handoff": "Validation and Handoff",
}

NEXT_QUESTIONS = {
    "inception": (
        "Who needs this ontology, what decision should it improve, "
        "and how will we know the workshop was useful?"
    ),
    "discovery": (
        "Describe one real business scenario from start to finish: "
        "who participates, what happens, and which records or systems are involved?"
    ),
    "event_discovery": (
        "Which important events or state changes happen in that scenario, "
        "and what triggers each one?"
    ),
    "story_to_question": (
        "What are the highest-priority questions this graph must answer for the user story?"
    ),
    "model_synthesis": (
        "Which candidate entities, relationships, events, and properties are needed "
        "to answer those questions?"
    ),
    "data_grounding": (
        "Which source tables, files, APIs, logs, or event streams can populate "
        "the high-priority model elements?"
    ),
    "adversarial_review": (
        "Which assumptions, contradictions, missing data, or over-modeled concepts "
        "must be challenged before handoff?"
    ),
    "validation_handoff": (
        "Which queries, mappings, risks, and action items should be packaged "
        "for the technical handoff?"
    ),
}

CLAIM_STATUSES = {
    "candidate",
    "confirmed",
    "assumed",
    "conflicting",
    "missing_evidence",
    "requires_data_mapping",
    "out_of_scope",
    "accepted",
    "open",
    "in_progress",
    "rejected",
    "revision_requested",
    "resolved",
}

WORKFLOW_COLLECTIONS = (
    "claims",
    "user_stories",
    "domain_events",
    "competency_questions",
    "model_candidates",
    "data_sources",
    "field_mappings",
    "assumptions",
    "contradictions",
    "risks",
    "decisions",
    "review_findings",
    "action_items",
    "validation_queries",
    "rdf_decisions",
)

REQUIRED_HANDOFF_ARTIFACTS = {
    "report_markdown", "report_html", "snapshot_html", "snapshot_json",
    "neptune_cypher", "neptune_nodes", "neptune_edges",
    "rdf_ontology", "rdf_instances", "rdf_jsonld", "rdf_shacl",
    "rdf_sparql", "rdf_mapping", "rdf_neptune_handoff", "workshop_zip",
}

_VIEW_ONLY_ITEM_FIELDS = {
    "effective_status", "verification_freshness", "verification_relevance",
}

_VIEW_ONLY_VALIDATION_FIELDS = {
    "handoff_approval", "handoff_alignment",
}

_COLLECTION_PREFIX = {
    "claims": "claim",
    "user_stories": "story",
    "domain_events": "event",
    "competency_questions": "question",
    "model_candidates": "model",
    "data_sources": "source",
    "field_mappings": "mapping",
    "assumptions": "assumption",
    "contradictions": "contradiction",
    "risks": "risk",
    "decisions": "decision",
    "review_findings": "finding",
    "action_items": "action",
    "validation_queries": "query",
    "rdf_decisions": "rdf",
}

_UNIQUE_KEYS = {
    "claims": ("text",),
    "user_stories": ("actor", "goal"),
    "domain_events": ("name",),
    "competency_questions": ("question",),
    "model_candidates": ("kind", "name"),
    "data_sources": ("name",),
    "field_mappings": ("source", "source_field"),
    "assumptions": ("text",),
    "contradictions": ("text",),
    "risks": ("text",),
    "decisions": ("text",),
    "review_findings": ("text",),
    "action_items": ("text",),
    "validation_queries": ("language", "question_id"),
    "rdf_decisions": ("topic",),
}

_JSON_COLLECTION_ALIASES = {
    "claim": "claims",
    "claims": "claims",
    "user_story": "user_stories",
    "user_stories": "user_stories",
    "story": "user_stories",
    "stories": "user_stories",
    "domain_event": "domain_events",
    "domain_events": "domain_events",
    "event": "domain_events",
    "events": "domain_events",
    "competency_question": "competency_questions",
    "competency_questions": "competency_questions",
    "question": "competency_questions",
    "questions": "competency_questions",
    "model_candidate": "model_candidates",
    "model_candidates": "model_candidates",
    "data_source": "data_sources",
    "data_sources": "data_sources",
    "source": "data_sources",
    "sources": "data_sources",
    "field_mapping": "field_mappings",
    "field_mappings": "field_mappings",
    "mapping": "field_mappings",
    "mappings": "field_mappings",
    "assumption": "assumptions",
    "assumptions": "assumptions",
    "contradiction": "contradictions",
    "contradictions": "contradictions",
    "risk": "risks",
    "risks": "risks",
    "decision": "decisions",
    "decisions": "decisions",
    "review_finding": "review_findings",
    "review_findings": "review_findings",
    "action_item": "action_items",
    "action_items": "action_items",
    "validation_query": "validation_queries",
    "validation_queries": "validation_queries",
    "query_candidate": "validation_queries",
    "query_candidates": "validation_queries",
    "rdf_decision": "rdf_decisions",
    "rdf_decisions": "rdf_decisions",
    "rdf_note": "rdf_decisions",
    "rdf_notes": "rdf_decisions",
}

_DATA_HINTS = (
    "table", "schema", "csv", "field", "column", "source", "api", "payload",
    "log", "stream", "database", "dataset", "데이터", "테이블", "스키마",
    "필드", "컬럼", "소스", "원천", "로그", "이벤트", "카탈로그",
)

_EVENT_HINTS = (
    "event", "created", "updated", "deleted", "approved", "rejected", "paid",
    "placed", "detected", "completed", "changed", "triggered", "이벤트", "발생",
    "생성", "변경", "승인", "거절", "결제", "주문", "검출", "탐지", "완료",
    "상태", "전이", "트리거",
)

_RDF_HINTS = ("rdf", "shacl", "sparql", "json-ld", "jsonld", "ttl", "turtle", "uri", "iri", "namespace", "네임스페이스")

REVIEWABLE_COLLECTIONS = {
    "claims",
    "assumptions",
    "contradictions",
    "review_findings",
    "risks",
    "action_items",
}

_STATUS_FOR_ACTION = {
    "confirm": "confirmed",
    "accept": "accepted",
    "reject": "rejected",
    "revise": "revision_requested",
    "resolve": "resolved",
    "start": "in_progress",
}

_TERMINAL_REVIEW_STATUSES = {"rejected", "resolved", "out_of_scope"}
_PENDING_REVIEW_STATUSES = {
    "candidate", "open", "assumed", "conflicting", "missing_evidence",
    "requires_data_mapping", "revision_requested",
}

_INITIAL_REVIEW_STATUSES = {
    "claims": {
        "candidate", "assumed", "conflicting", "missing_evidence",
        "requires_data_mapping", "out_of_scope",
    },
    "assumptions": {"candidate", "assumed", "open"},
    "contradictions": {"candidate", "conflicting", "open"},
    "review_findings": {"candidate", "open"},
    "risks": {"candidate", "open"},
    "action_items": {"candidate", "open"},
}

REVIEW_CATEGORIES = {
    "ambiguity",
    "contradiction",
    "causality",
    "event_modeling",
    "over_modeling",
    "sensitivity",
}


def _now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _clean_item(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if v is not None}


def _has_text(item: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


_PLACEHOLDER_TEXT = {
    "-", "?", "x", "na", "n/a", "none", "null", "tbd", "todo",
    "unknown", "unspecified", "pending", "미정", "불명", "모름",
    "未定", "不明",
}


def _meaningful_text(item: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = item.get(key)
        if not isinstance(value, str):
            continue
        normalized = re.sub(r"\s+", " ", value).strip().lower().rstrip(".")
        if normalized in _PLACEHOLDER_TEXT:
            continue
        if len(re.sub(r"[^\w\u0080-\uffff]", "", normalized)) >= 2:
            return True
    return False


def _meaningful_values(value: Any) -> list[str]:
    return [
        str(item).strip() for item in _list(value)
        if _meaningful_text({"value": str(item)}, "value")
    ]


def _readiness_status(value: str | None) -> str:
    raw = (value or "unknown").strip().lower().replace(" ", "_")
    aliases = {
        "available": "available",
        "partial": "partial",
        "partially_available": "partial",
        "missing": "missing",
        "derived": "derived",
        "unknown": "unknown",
    }
    return aliases.get(raw, "unknown")


def _event_modeling_class(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "event": "event_node", "domain_event": "event_node",
        "event_node": "event_node", "node": "event_node",
        "relationship": "relation", "relation": "relation", "edge": "relation",
        "attribute": "property", "property": "property",
        "not_modeled": "not_modeled", "out_of_scope": "not_modeled",
    }
    return aliases.get(raw, "")


def _status(item: dict[str, Any]) -> str:
    return str(item.get("status") or "candidate").strip().lower()


def _active(item: Any) -> bool:
    return isinstance(item, dict) and _status(item) not in {
        "rejected", "out_of_scope"
    }


def _high_priority(item: dict[str, Any]) -> bool:
    return str(item.get("priority") or "").strip().lower() in {
        "high", "critical", "must", "p0", "p1"
    }


def _ids(item: dict[str, Any], *keys: str) -> set[str]:
    values: set[str] = set()
    for key in keys:
        value = item.get(key)
        if isinstance(value, list):
            values.update(str(v) for v in value if v not in (None, ""))
        elif value not in (None, ""):
            values.add(str(value))
    return values


def _has_merge_conflicts(item: dict[str, Any]) -> bool:
    return bool(_list(item.get("merge_conflicts")))


def _allowed_statuses(collection: str, current: str) -> set[str]:
    if current in _TERMINAL_REVIEW_STATUSES:
        return {current, "revision_requested"}
    common = {"confirmed", "rejected", "revision_requested", "resolved"}
    if collection == "action_items":
        return common | {"accepted", "in_progress"}
    return common | {"accepted"}


def _history_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in item.items()
        if key not in {"history", "created_at", "updated_at"}
    }


def _system_change_item(item: dict[str, Any], changes: dict[str, Any],
                        action: str, note: str) -> None:
    before = copy.deepcopy(item)
    item.update(copy.deepcopy(changes))
    item["updated_at"] = _now()
    item.setdefault("history", []).append({
        "at": item["updated_at"],
        "actor": "system",
        "action": action,
        "note": note,
        "before": _history_snapshot(before),
        "after": _history_snapshot(item),
    })


def _clear_merge_conflicts(item: dict[str, Any], changed_fields: set[str]) -> None:
    remaining = []
    for proposal in _list(item.get("merge_conflicts")):
        fields = {
            key: value for key, value in _dict(proposal.get("fields")).items()
            if key not in changed_fields
        }
        if fields:
            updated = copy.deepcopy(proposal)
            updated["fields"] = fields
            remaining.append(updated)
    if remaining:
        item["merge_conflicts"] = remaining
    else:
        item.pop("merge_conflicts", None)


def _sanitize_incoming_item(collection: str,
                            item: dict[str, Any]) -> dict[str, Any]:
    clean = _clean_item(copy.deepcopy(item or {}))
    if collection == "validation_queries":
        for field in (
            "verification_evidence", "last_verification",
            "last_static_validation", "verified_at",
        ):
            clean.pop(field, None)
        clean["status"] = "candidate"
        readiness = str(clean.get("readiness") or "candidate").lower()
        clean["readiness"] = readiness if readiness in {
            "candidate", "ready_to_draft", "needs_model", "seed_only"
        } else "candidate"
    elif collection == "competency_questions":
        for field in (
            "last_verification", "verification_status", "verified_at",
        ):
            clean.pop(field, None)
        if str(clean.get("query_readiness") or "").lower() == "verified":
            clean["query_readiness"] = "ready_to_draft"
    if collection in REVIEWABLE_COLLECTIONS:
        requested_status = str(clean.get("status") or "candidate").lower()
        allowed_initial = _INITIAL_REVIEW_STATUSES[collection]
        if requested_status not in allowed_initial:
            clean["requested_status"] = requested_status
            clean["status"] = (
                "candidate" if "candidate" in allowed_initial else "open")
    return clean


class WorkflowState:
    """Mutable AI-ODLC state with deterministic gate checks."""

    def __init__(self, payload: dict[str, Any] | None = None):
        self.data = self._default()
        if payload:
            self.load(payload)

    @staticmethod
    def _default() -> dict[str, Any]:
        ts = _now()
        return {
            "version": "ai-odlc-v2",
            "current_stage": "inception",
            "started_at": ts,
            "updated_at": ts,
            "language": "ko",
            "scope": "",
            "active_question": NEXT_QUESTIONS["inception"],
            "claims": [],
            "user_stories": [],
            "domain_events": [],
            "competency_questions": [],
            "model_candidates": [],
            "data_sources": [],
            "field_mappings": [],
            "assumptions": [],
            "contradictions": [],
            "risks": [],
            "decisions": [],
            "review_findings": [],
            "action_items": [],
            "validation_queries": [],
            "rdf_decisions": [],
            "last_extraction": {},
            "last_validation": {},
            "handoff_manifest": {},
            "review_runs": [],
            "transition_history": [],
        }

    def reset(self) -> None:
        self.data = self._default()

    def load(self, payload: dict[str, Any] | None) -> None:
        if not isinstance(payload, dict):
            self.reset()
            return
        base = self._default()
        for key in base:
            if key in payload:
                base[key] = copy.deepcopy(payload[key])
        if base.get("current_stage") not in STAGES:
            base["current_stage"] = "inception"
        if not base.get("active_question"):
            base["active_question"] = NEXT_QUESTIONS[base["current_stage"]]
        for key in WORKFLOW_COLLECTIONS:
            base[key] = _list(base.get(key))
            for item in base[key]:
                if isinstance(item, dict):
                    for field in _VIEW_ONLY_ITEM_FIELDS:
                        item.pop(field, None)
        if not isinstance(base.get("last_extraction"), dict):
            base["last_extraction"] = {}
        if not isinstance(base.get("last_validation"), dict):
            base["last_validation"] = {}
        else:
            for field in _VIEW_ONLY_VALIDATION_FIELDS:
                base["last_validation"].pop(field, None)
        if not isinstance(base.get("handoff_manifest"), dict):
            base["handoff_manifest"] = {}
        if not isinstance(base.get("review_runs"), list):
            base["review_runs"] = []
        if not isinstance(base.get("transition_history"), list):
            base["transition_history"] = []
        self.data = base
        self.touch()

    def touch(self) -> None:
        self.data["updated_at"] = _now()

    def review_source_fingerprint(self) -> str:
        return _review_source_fingerprint(self.data)

    def handoff_source_fingerprint(self, graph_fingerprint: str = "") -> str:
        return _handoff_source_fingerprint(self.data, graph_fingerprint)

    def query_source_fingerprint(self, tbox: Any = None,
                                 snapshot: Any = None) -> str:
        return _query_source_fingerprint(tbox, snapshot, self.data)

    def record_handoff_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(manifest, dict):
            raise ValueError("handoff manifest must be an object")
        recorded = copy.deepcopy(manifest)
        artifacts = _dict(recorded.get("artifacts"))
        missing = sorted(
            key for key in REQUIRED_HANDOFF_ARTIFACTS
            if not artifacts.get(key)
        )
        recorded.setdefault("generated_at", _now())
        recorded["missing_artifacts"] = missing
        recorded["status"] = "complete" if not missing else "incomplete"
        self.data["handoff_manifest"] = recorded
        self.touch()
        return recorded

    def to_dict(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        out = copy.deepcopy(self.data)
        current_query_fingerprint = _dict(context).get(
            "query_source_fingerprint")
        for query in _list(out.get("validation_queries")):
            if (not isinstance(query, dict)
                    or str(query.get("language") or "").lower() != "opencypher"):
                continue
            evidence = _list(query.get("verification_evidence"))
            linked_question = next((
                item for item in _list(out.get("competency_questions"))
                if isinstance(item, dict)
                and str(item.get("id") or "") == str(query.get("question_id") or "")
            ), None)
            relevant = bool(linked_question) and _query_covers_answer_shape(
                query, linked_question)
            current = bool(current_query_fingerprint) and any(
                isinstance(item, dict) and bool(item.get("ok"))
                and item.get("query_match") is True
                and item.get("source_fingerprint") == current_query_fingerprint
                for item in evidence
            )
            query["verification_relevance"] = (
                "match" if relevant else "mismatch")
            if evidence:
                query["verification_freshness"] = (
                    "current" if current else
                    "stale" if current_query_fingerprint else "unknown")
            elif _status(query) == "verified":
                query["verification_freshness"] = "unproven"
            if _status(query) == "verified" and not relevant:
                query["effective_status"] = "needs_fix"
            elif (_status(query) == "verified"
                    and query.get("verification_freshness") != "current"):
                query["effective_status"] = query["verification_freshness"]
            else:
                query["effective_status"] = _status(query)
        if out.get("last_validation"):
            out["last_validation"]["freshness"] = self._validation_freshness(
                context)
        out["stage_label"] = STAGE_LABELS.get(
            out.get("current_stage"), out.get("current_stage", ""))
        gates = self.gates(context)
        out["gates"] = gates
        if out.get("last_validation"):
            static_check = next((
                check for check in gates["validation_handoff"]["checks"]
                if check.get("id") == "handoff.static_validation"
            ), {})
            out["last_validation"]["handoff_approval"] = (
                "approved" if static_check.get("status") == "pass"
                else "not_approved"
            )
            out["last_validation"]["handoff_alignment"] = copy.deepcopy(
                _dict(static_check.get("evidence")))
        passed = sum(1 for g in gates.values() if g["status"] == "pass")
        out["progress"] = {
            "passed": passed,
            "total": len(STAGES),
            "percent": round((passed / len(STAGES)) * 100),
        }
        return out

    def _validation_freshness(self,
                              context: dict[str, Any] | None = None) -> str:
        validation = _dict(self.data.get("last_validation"))
        expected = validation.get("source_fingerprint")
        current = _dict(context).get("rdf_validation_source_fingerprint")
        if not validation:
            return "not_run"
        if not expected or not current:
            return "unknown"
        return "current" if expected == current else "stale"

    def current_query_evidence(
            self, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return only successful, relevant evidence for the current query inputs."""
        current_fingerprint = _dict(context).get("query_source_fingerprint")
        if not current_fingerprint:
            return []
        high_questions = [
            item for item in _list(self.data.get("competency_questions"))
            if isinstance(item, dict) and _active(item) and _high_priority(item)
        ]
        questions = {
            str(item.get("id")): item for item in high_questions if item.get("id")
        }
        results: list[dict[str, Any]] = []
        for query in _list(self.data.get("validation_queries")):
            if (not isinstance(query, dict)
                    or str(query.get("language") or "").lower() != "opencypher"
                    or _status(query) != "verified"
                    or _has_merge_conflicts(query)):
                continue
            question = questions.get(str(query.get("question_id") or ""))
            if question is None or not _query_covers_answer_shape(query, question):
                continue
            evidence = next((
                item for item in reversed(_list(query.get("verification_evidence")))
                if isinstance(item, dict) and bool(item.get("ok"))
                and item.get("query_match") is True
                and item.get("source_fingerprint") == current_fingerprint
            ), None)
            if evidence is None:
                continue
            results.append({
                "question_id": query.get("question_id"),
                "question": question.get("question") or question.get("text"),
                "cypher": query.get("query"),
                "count": evidence.get("count", 0),
                "columns": copy.deepcopy(evidence.get("columns") or []),
                "verified_at": evidence.get("verified_at"),
                "source_fingerprint": current_fingerprint,
            })
        return results

    def _next_id(self, collection: str, prefix: str) -> str:
        used = {str(i.get("id")) for i in _list(self.data.get(collection))
                if isinstance(i, dict) and i.get("id")}
        n = len(used) + 1
        while f"{prefix}-{n:03d}" in used:
            n += 1
        return f"{prefix}-{n:03d}"

    def add_item(self, collection: str, prefix: str, item: dict[str, Any]) -> dict[str, Any]:
        if collection not in self.data or not isinstance(self.data[collection], list):
            raise ValueError(f"unknown workflow collection {collection}")
        clean = _sanitize_incoming_item(collection, item)
        item_id = clean.get("id")
        if item_id and any(
                isinstance(existing, dict) and existing.get("id") == item_id
                for existing in self.data[collection]):
            raise ValueError(f"duplicate {collection} item id {item_id}")
        requested_stage = clean.get("stage")
        if requested_stage is not None and requested_stage not in STAGES:
            raise ValueError(f"unknown workflow stage {requested_stage}")
        if not clean.get("id"):
            clean["id"] = self._next_id(collection, prefix)
        clean.setdefault("stage", self.data["current_stage"])
        clean.setdefault("status", "candidate")
        clean.setdefault("source", "user")
        clean.setdefault("created_at", _now())
        clean["updated_at"] = _now()
        clean.setdefault("history", [])
        self.data[collection].append(clean)
        self.touch()
        return clean

    def add_unique_item(self, collection: str, prefix: str,
                        item: dict[str, Any]) -> dict[str, Any]:
        """Add evidence without silently overwriting a conflicting existing row.

        Equivalent rows only receive previously absent fields. Non-empty conflicting
        values are retained as a pending merge proposal for explicit human review.
        """
        clean = _sanitize_incoming_item(collection, item)
        existing = self._find_equivalent(collection, clean)
        if existing:
            before = copy.deepcopy(existing)
            changed = False
            conflicts: dict[str, dict[str, Any]] = {}
            ignored = {
                "id", "created_at", "updated_at", "history", "source", "stage",
            }
            if collection in REVIEWABLE_COLLECTIONS or collection == "validation_queries":
                ignored.add("status")
            if collection == "validation_queries":
                ignored.add("readiness")
            for key, value in clean.items():
                if key in ignored or value in (None, "", [], {}):
                    continue
                if not existing.get(key):
                    existing[key] = value
                    changed = True
                elif _norm_value(existing.get(key)) != _norm_value(value):
                    conflicts[key] = {
                        "existing": copy.deepcopy(existing.get(key)),
                        "incoming": copy.deepcopy(value),
                    }
            if conflicts:
                existing.setdefault("merge_conflicts", [])
                proposal = {
                    "at": _now(),
                    "source": clean.get("source", "unknown"),
                    "fields": conflicts,
                }
                if proposal["fields"] not in [p.get("fields") for p in existing["merge_conflicts"]]:
                    existing["merge_conflicts"].append(proposal)
                    changed = True
            if changed:
                existing["updated_at"] = _now()
                existing.setdefault("history", []).append({
                    "at": existing["updated_at"],
                    "actor": "system",
                    "action": "deduplicate_merge_proposed" if conflicts
                    else "deduplicate_fill",
                    "note": "Equivalent evidence was merged without overwriting competing values.",
                    "before": _history_snapshot(before),
                    "after": _history_snapshot(existing),
                })
                self.touch()
            return existing
        return self.add_item(collection, prefix, clean)

    def _find_equivalent(self, collection: str,
                         item: dict[str, Any]) -> dict[str, Any] | None:
        keys = _UNIQUE_KEYS.get(collection, ("text", "name", "question"))
        if any(item.get(key) in (None, "", [], {}) for key in keys):
            return None
        comparable = [
            k for k in keys
            if item.get(k) not in (None, "", [], {})
        ]
        if not comparable:
            return None
        for existing in _list(self.data.get(collection)):
            if not isinstance(existing, dict):
                continue
            if all(_norm_value(existing.get(k)) == _norm_value(item.get(k))
                   for k in comparable):
                return existing
        return None

    def record_answer(self, text: str, stage: str | None = None,
                      role: str = "customer",
                      status: str = "candidate",
                      source: str = "workflow_answer") -> dict[str, Any]:
        current = self.data["current_stage"]
        if stage is not None and stage not in STAGES:
            raise ValueError(f"unknown workflow stage {stage}")
        if stage is not None and stage != current:
            raise ValueError(
                f"answers can only be recorded for the current stage {current}; "
                "advance the workflow first"
            )
        stage = current
        status = status if status in CLAIM_STATUSES else "candidate"
        story_ids = [
            str(item.get("id")) for item in _list(self.data.get("user_stories"))
            if _active(item) and item.get("id") and _high_priority(item)
        ]
        claim = self.add_item("claims", "claim", {
            "text": text,
            "stage": stage,
            "role": role,
            "status": status,
            "source": source,
            **({"story_ids": story_ids} if stage == "discovery" and story_ids else {}),
        })
        self.touch()
        return claim

    def process_answer(self, text: str, stage: str | None = None,
                       role: str = "customer",
                       status: str = "candidate",
                       source: str = "workflow_answer",
                       extracted: dict[str, Any] | None = None,
                       context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Record an answer and extract workshop evidence from it.

        This is intentionally deterministic. It gives the AI-ODLC API a useful
        offline baseline even when no external LLM is configured; an assistant
        can still provide richer structured objects in the optional extracted
        payload.
        """
        claim = self.record_answer(text, stage, role, status, source)
        active_stage = claim.get("stage") or self.data["current_stage"]
        generated = infer_workflow_items(text, active_stage, self.data, context)
        generated = _merge_extracted(generated, extracted)
        added: dict[str, list[dict[str, Any]]] = {k: [] for k in WORKFLOW_COLLECTIONS}
        added["claims"].append(claim)

        for collection, items in generated.items():
            if collection not in self.data or not isinstance(items, list):
                continue
            prefix = _COLLECTION_PREFIX.get(collection, collection.rstrip("s"))
            for item in items:
                if not isinstance(item, dict):
                    continue
                # Stage is capture provenance, not a client-selected destination.
                # Comprehensive early answers may populate later-stage collections,
                # but every extracted object records where it was actually captured.
                item["stage"] = active_stage
                item.setdefault("source", source)
                item.setdefault("claim_id", claim.get("id"))
                if collection == "competency_questions" and not _ids(
                        item, "story_id", "story_ids", "user_story_id"):
                    story_ids = [
                        str(story.get("id"))
                        for story in _list(self.data.get("user_stories"))
                        if _active(story) and story.get("id") and _high_priority(story)
                    ]
                    if len(story_ids) == 1:
                        item["story_ids"] = story_ids
                if collection == "model_candidates" and not _ids(
                        item, "story_id", "story_ids", "event_id", "event_ids",
                        "question_id", "question_ids", "data_source_id",
                        "data_source_ids"):
                    question_ids = _candidate_question_links(
                        item, self.data.get("competency_questions"))
                    if question_ids:
                        item["question_ids"] = question_ids
                added_item = self.add_unique_item(collection, prefix, item)
                added[collection].append(added_item)

        self._refresh_query_candidates(context)
        self.data["active_question"] = self.next_question(context)
        self.data["last_extraction"] = {
            "claim_id": claim.get("id"),
            "stage": active_stage,
            "added": {
                key: len(value)
                for key, value in added.items()
                if value and key != "claims"
            },
            "summary": summarize_extraction(added),
        }
        self.touch()
        return {"claim": claim, "added": added, "summary": self.data["last_extraction"]}

    def _refresh_query_candidates(self, context: dict[str, Any] | None = None) -> None:
        graph = _dict((context or {}).get("graph"))
        has_model = bool(graph.get("entities")) or bool(self.data.get("model_candidates"))
        if not has_model:
            return
        for question in _list(self.data.get("competency_questions")):
            if not isinstance(question, dict):
                continue
            qtext = question.get("question") or question.get("text")
            if not qtext:
                continue
            question.setdefault("query_readiness", "ready_to_draft" if has_model else "needs_model")
            answer_shape = question.get("expected_answer_shape") or question.get("answer_shape")
            query = question.get("cypher_candidate") or _cypher_seed(qtext, answer_shape)
            if not _query_covers_answer_shape({"query": query}, question):
                query = _cypher_seed(qtext, answer_shape)
                question["query_readiness"] = "ready_to_draft"
            question["cypher_candidate"] = query
            sparql = question.get("sparql_candidate")
            if not sparql or any(
                    f":{_safe_label(value)}" not in sparql
                    for value in _meaningful_values(answer_shape)):
                sparql = _sparql_seed(qtext, answer_shape)
            question["sparql_candidate"] = sparql
            self.add_unique_item("validation_queries", "query", {
                "question_id": question.get("id"),
                "question": qtext,
                "language": "openCypher",
                "query": query,
                "status": "candidate",
                "readiness": question.get("query_readiness"),
                "stage": question.get("stage", self.data["current_stage"]),
                "source": question.get("source", "workflow"),
            })
            self.add_unique_item("validation_queries", "query", {
                "question_id": question.get("id"),
                "question": qtext,
                "language": "SPARQL",
                "query": question.get("sparql_candidate"),
                "status": "candidate",
                "readiness": "seed_only",
                "stage": question.get("stage", self.data["current_stage"]),
                "source": question.get("source", "workflow"),
            })

    def next_question(self, context: dict[str, Any] | None = None) -> str:
        """Return one focused question at or after the current stage."""
        gates = self.gates(context)
        stage = self.data.get("current_stage")
        start = STAGES.index(stage) if stage in STAGES else 0
        for candidate in STAGES[start:]:
            gate = gates.get(candidate, {})
            if gate.get("status") != "pass":
                stage = candidate
                missing = gate.get("missing") or []
                if missing:
                    return _stage_question(candidate, missing[0], self.data)
                return NEXT_QUESTIONS.get(candidate, NEXT_QUESTIONS["inception"])
        return NEXT_QUESTIONS.get(stage, NEXT_QUESTIONS["validation_handoff"])

    def start(self, language: str | None = None, scope: str | None = None,
              reset: bool = False) -> dict[str, Any]:
        if reset:
            self.reset()
        if language:
            self.data["language"] = language
        if scope is not None:
            self.data["scope"] = scope
        current = self.data.get("current_stage", "inception")
        self.data["active_question"] = NEXT_QUESTIONS[current]
        self.touch()
        return self.to_dict()

    def advance(self, stage: str | None = None, force: bool = False,
                context: dict[str, Any] | None = None,
                reason: str | None = None,
                actor: str = "operator") -> dict[str, Any]:
        current = self.data["current_stage"]
        idx = STAGES.index(current)
        if idx >= len(STAGES) - 1:
            raise ValueError("workflow is already at the final stage")
        expected = STAGES[idx + 1]
        target = stage or expected
        if target not in STAGES:
            raise ValueError(f"unknown workflow stage {target}")
        if target != expected:
            direction = "backward" if STAGES.index(target) <= idx else "skipped"
            raise ValueError(
                f"illegal {direction} transition {current} -> {target}; "
                f"the only legal target is {expected}"
            )
        reason = (reason or "").strip()
        if force and len(reason) < 8:
            raise ValueError("force advance requires a reason of at least 8 characters")
        gates = self.gates(context)
        blocking = [
            (name, gates[name]) for name in STAGES[:idx + 1]
            if gates[name]["status"] != "pass"
        ]
        if not force and blocking:
            blocked_stage, blocked_gate = blocking[0]
            return {
                "ok": False,
                "blocked": True,
                "stage": current,
                "blocked_stage": blocked_stage,
                "gate": blocked_gate,
                "workflow": self.to_dict(context),
            }
        transition = {
            "from": current,
            "to": target,
            "forced": bool(force),
            "reason": reason if force else "",
            "actor": actor or "operator",
            "at": _now(),
            "bypassed_gates": [name for name, _gate_data in blocking] if force else [],
        }
        self.data["current_stage"] = target
        self.data["active_question"] = NEXT_QUESTIONS[target]
        self.data.setdefault("transition_history", []).append(transition)
        self.touch()
        return {
            "ok": True,
            "stage": target,
            "transition": transition,
            "workflow": self.to_dict(context),
        }

    def get_item(self, collection: str, item_id: str) -> dict[str, Any]:
        if collection not in WORKFLOW_COLLECTIONS:
            raise ValueError(f"unknown workflow collection {collection}")
        for item in _list(self.data.get(collection)):
            if isinstance(item, dict) and item.get("id") == item_id:
                return item
        raise ValueError(f"unknown {collection} item {item_id}")

    def decide_item(self, collection: str, item_id: str, action: str,
                    changes: dict[str, Any] | None = None,
                    note: str | None = None,
                    actor: str = "operator",
                    linked_action: dict[str, Any] | None = None) -> dict[str, Any]:
        """Apply an explicit review decision and preserve its before/after history."""
        action = (action or "").strip().lower()
        if action not in {"update", "merge", *_STATUS_FOR_ACTION.keys()}:
            raise ValueError(f"unsupported workflow item action {action}")
        if collection not in WORKFLOW_COLLECTIONS:
            raise ValueError(f"unknown workflow collection {collection}")
        if action not in {"update", "merge"} and collection not in REVIEWABLE_COLLECTIONS:
            raise ValueError(f"collection {collection} does not support status decisions")
        if not (note or "").strip():
            raise ValueError("workflow item decisions require a decision note")
        changes = _clean_item(copy.deepcopy(changes or {}))
        protected = {
            "id", "created_at", "updated_at", "history",
            "source", "requested_status", "verification_evidence",
            "last_verification", "last_static_validation", "verified_at",
            "linked_action_id", "linked_action_ids",
            "merge_conflicts", "issue_key",
            "review_runs", "transition_history", "handoff_manifest",
            "gates", "progress", "last_validation", "last_extraction",
        }
        if collection in REVIEWABLE_COLLECTIONS or collection == "validation_queries":
            protected.add("status")
        if protected.intersection(changes):
            raise ValueError(
                "identity, provenance, timestamps, history, and status cannot be patched directly"
            )
        if any(str(key).startswith("_") for key in changes):
            raise ValueError("internal workflow fields cannot be patched")
        if action in {"update", "merge"} and not changes:
            raise ValueError(f"{action} requires at least one changed field")
        if action == "merge" and not (note or "").strip():
            raise ValueError("merge requires a decision note")
        review_metadata = {
            "severity", "category", "evidence_id", "evidence_ids",
        }
        if review_metadata.intersection(changes) and not (note or "").strip():
            raise ValueError(
                "changing review classification or evidence links requires a decision note"
            )

        item = self.get_item(collection, item_id)
        before = copy.deepcopy(item)
        old_status = str(item.get("status") or "candidate")
        if collection in REVIEWABLE_COLLECTIONS and old_status not in CLAIM_STATUSES:
            raise ValueError(f"unknown workflow item status {old_status}")
        new_status = _STATUS_FOR_ACTION.get(action, old_status)
        allowed = _allowed_statuses(collection, old_status)
        if action not in {"update", "merge"} and new_status not in allowed:
            raise ValueError(
                f"illegal {collection} status transition {old_status} -> {new_status}"
            )
        action_record = None
        if (action == "accept" and collection != "action_items"
                and str(item.get("severity") or "").lower() in {"high", "critical"}):
            linked_action = _clean_item(copy.deepcopy(linked_action or {}))
            if not _has_text(linked_action, "text") or not _has_text(linked_action, "owner"):
                raise ValueError(
                    "accepting a high/critical review item requires a linked action with text and owner"
                )
            linked_action.setdefault("status", "accepted")
            linked_action.setdefault("stage", item.get("stage", "adversarial_review"))
            linked_action.setdefault("source", "review_decision")
            linked_action["evidence_ids"] = sorted(
                _ids(linked_action, "evidence_id", "evidence_ids") | {item_id})
            action_record = self.add_unique_item(
                "action_items", "action", linked_action)
            if _status(action_record) != "accepted":
                _system_change_item(action_record, {"status": "accepted"},
                                    "linked_action_accepted",
                                    "Created atomically from an explicit review acceptance.")

        applied_changes = copy.deepcopy(changes)
        if action == "revise":
            applied_changes = {
                key: value for key, value in applied_changes.items()
                if key not in {"status", "readiness"}
            }
        for key, value in applied_changes.items():
            item[key] = value
        if collection == "validation_queries" and {
                "query", "question", "question_id", "language"
        }.intersection(applied_changes):
            item.pop("verification_evidence", None)
            item.pop("last_verification", None)
            item["status"] = "candidate"
            item["readiness"] = (
                "seed_only" if str(item.get("language") or "").lower() == "sparql"
                else "ready_to_draft"
            )
        if collection == "competency_questions" and {
                "question", "text", "expected_answer_shape", "answer_shape",
                "story_id", "story_ids", "priority"
        }.intersection(applied_changes):
            item.pop("last_verification", None)
            item.pop("verification_status", None)
            item["query_readiness"] = "ready_to_draft"
        if action not in {"update", "merge"}:
            item["status"] = new_status
        if applied_changes:
            _clear_merge_conflicts(item, set(applied_changes))
        if action_record:
            item["linked_action_ids"] = sorted(
                _ids(item, "linked_action_id", "linked_action_ids")
                | {str(action_record.get("id"))})
        item["updated_at"] = _now()
        history_entry = {
            "at": item["updated_at"],
            "actor": actor or "operator",
            "action": action,
            "note": (note or "").strip(),
            "before": _history_snapshot(before),
            "after": _history_snapshot(item),
        }
        item.setdefault("history", []).append(history_entry)
        self.touch()
        return item

    def add_review(self, findings: list[dict] | None = None,
                   assumptions: list[dict] | None = None,
                   risks: list[dict] | None = None,
                   action_items: list[dict] | None = None,
                   contradictions: list[dict] | None = None) -> dict[str, Any]:
        added = {
            "review_findings": [], "assumptions": [], "contradictions": [],
            "risks": [], "action_items": [],
        }
        for item in findings or []:
            added["review_findings"].append(
                self.add_unique_item("review_findings", "finding", item))
        for item in assumptions or []:
            added["assumptions"].append(
                self.add_unique_item("assumptions", "assumption", item))
        for item in contradictions or []:
            added["contradictions"].append(
                self.add_unique_item("contradictions", "contradiction", item))
        for item in risks or []:
            added["risks"].append(self.add_unique_item("risks", "risk", item))
        for item in action_items or []:
            added["action_items"].append(
                self.add_unique_item("action_items", "action", item))
        return added

    def generate_review(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run bounded deterministic semantic checks; no retry or background loop."""
        findings: list[dict[str, Any]] = []
        risks: list[dict[str, Any]] = []
        assumptions: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []
        action_items: list[dict[str, Any]] = []
        # Ambiguity and contradictions: explicit merge conflicts and conflicting claims.
        for collection in WORKFLOW_COLLECTIONS:
            for item in _list(self.data.get(collection)):
                if not isinstance(item, dict) or not _has_merge_conflicts(item):
                    continue
                findings.append(_review_finding(
                    "ambiguity", "high",
                    f"{collection} item {item.get('id')} has unresolved competing values.",
                    item.get("stage", "adversarial_review"), [item.get("id")]))

        claims = [item for item in _list(self.data.get("claims")) if _active(item)]
        for idx, left in enumerate(claims):
            for right in claims[idx + 1:]:
                if not _claims_conflict(left, right):
                    continue
                issue_key = "claim-conflict:" + ":".join(sorted([
                    str(left.get("id")), str(right.get("id"))]))
                contradictions.append({
                    "issue_key": issue_key,
                    "text": f"Claims {left.get('id')} and {right.get('id')} assert incompatible values.",
                    "category": "contradiction",
                    "severity": "critical",
                    "status": "open",
                    "stage": "adversarial_review",
                    "evidence_ids": [left.get("id"), right.get("id")],
                    "source": "automatic_adversarial_review",
                })

        # Unsupported causality language requires external evidence or a decision.
        causal_pattern = re.compile(
            r"\b(cause[sd]?|caused by|leads? to|results? in|because of|drives?)\b|"
            r"(원인|때문|유발|초래|영향을 준다)", re.I)
        for claim in claims:
            if causal_pattern.search(str(claim.get("text") or "")) and not _has_text(
                    claim, "evidence", "evidence_id", "validation_method"):
                findings.append(_review_finding(
                    "causality", "high",
                    f"Claim {claim.get('id')} makes a causal assertion without validation evidence.",
                    claim.get("stage", "discovery"), [claim.get("id")]))

        # Event-vs-edge mistakes: temporal/contextual properties modeled as bare relations.
        for model in _list(self.data.get("model_candidates")):
            if not _active(model) or str(model.get("kind") or "").lower() != "relation":
                continue
            props = {str(key).lower() for key in _dict(model.get("properties"))}
            if props & {"time", "timestamp", "date", "quantity", "amount", "channel", "status"}:
                findings.append(_review_finding(
                    "event_modeling", "high",
                    f"Relation {model.get('name')} carries event context and may require an event node decision.",
                    "model_synthesis", [model.get("id")]))

        # Duplicate and over-generalized model concepts.
        model_items = [item for item in _list(self.data.get("model_candidates")) if _active(item)]
        for idx, left in enumerate(model_items):
            for right in model_items[idx + 1:]:
                if _similar_model_names(left.get("name"), right.get("name")):
                    findings.append(_review_finding(
                        "over_modeling", "medium",
                        f"Model candidates {left.get('name')} and {right.get('name')} may duplicate the same concept.",
                        "model_synthesis", [left.get("id"), right.get("id")]))
        for model in model_items:
            if not _candidate_has_link(model):
                findings.append(_review_finding(
                    "over_modeling", "high",
                    f"Model candidate {model.get('name') or model.get('id')} has no traceable story, event, question, or source need.",
                    "model_synthesis", [model.get("id")]))

        # Sensitive data must have an explicit handling/necessity decision.
        sensitive_pattern = re.compile(
            r"(email|phone|address|birth|ssn|passport|health|medical|salary|"
            r"이메일|전화|주소|생년|주민|여권|의료|건강|급여)", re.I)
        for source in _list(self.data.get("data_sources")):
            haystack = " ".join([
                str(source.get("name") or ""),
                " ".join(str(key) for key in _dict(source.get("fields"))),
                str(source.get("sensitivity") or ""),
            ])
            sensitive = sensitive_pattern.search(haystack) or str(
                source.get("sensitivity") or "").lower() in {"high", "restricted", "confidential", "pii"}
            if sensitive and not _has_text(source, "handling", "purpose", "retention", "privacy_decision"):
                risks.append({
                    "text": f"Data source {source.get('name')} appears sensitive without a handling or necessity decision.",
                    "category": "sensitivity", "severity": "high", "status": "open",
                    "stage": "data_grounding", "evidence_ids": [source.get("id")],
                    "source": "automatic_adversarial_review",
                })

        review_fingerprint = _review_source_fingerprint(self.data, context)
        added = self.add_review(
            findings=findings,
            assumptions=assumptions,
            contradictions=contradictions,
            risks=risks,
            action_items=action_items,
        )
        for collection in ("review_findings", "contradictions", "risks"):
            for item in added[collection]:
                previous = item.get("last_seen_review_fingerprint")
                if (previous and previous != review_fingerprint
                        and _status(item) == "resolved"):
                    _system_change_item(item, {
                        "status": "revision_requested",
                        "last_seen_review_fingerprint": review_fingerprint,
                    }, "automatic_issue_recurred",
                       "The same issue was detected again after material evidence changed.")
                elif previous != review_fingerprint:
                    _system_change_item(item, {
                        "last_seen_review_fingerprint": review_fingerprint,
                    }, "automatic_issue_observed",
                       "The bounded review observed this issue in the current evidence.")
        run = {
            "id": f"review-run-{len(_list(self.data.get('review_runs'))) + 1:03d}",
            "at": _now(),
            "source": "automatic_adversarial_review",
            "categories_assessed": sorted(REVIEW_CATEGORIES),
            "reviewed_evidence_count": _review_evidence_count(self.data),
            "source_fingerprint": review_fingerprint,
            "result": "issues_found" if findings or contradictions or risks else "no_issue_detected",
            "new_item_ids": [
                item.get("id") for collection in added.values() for item in collection
                if isinstance(item, dict) and item.get("id")
            ],
        }
        self.data.setdefault("review_runs", []).append(run)
        self.touch()
        added["review_run"] = run
        return added

    def record_query_verification(self, question: str | None, cypher: str,
                                  result: dict[str, Any],
                                  context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Attach openCypher execution evidence to matching workflow query seeds."""
        question = (question or "").strip()
        cypher = (cypher or "").strip()
        if not question and not cypher:
            return {"updated": 0}
        ok = bool(result.get("ok"))
        evidence = {
            "verified_at": _now(),
            "ok": ok,
            "query_match": False,
            "source_fingerprint": _dict(context).get(
                "query_source_fingerprint"),
            "count": result.get("count", 0),
            "columns": result.get("columns", []),
            "error": result.get("error"),
        }
        updated = 0
        qualified = 0
        latest_evidence = evidence
        matched_question_ids: set[str] = set()
        question_by_id = {
            str(item.get("id")): item
            for item in _list(self.data.get("competency_questions"))
            if isinstance(item, dict) and item.get("id")
        }
        for item in _list(self.data.get("validation_queries")):
            if not isinstance(item, dict):
                continue
            if str(item.get("language", "")).lower() != "opencypher":
                continue
            if not _query_matches(item, question, cypher):
                continue
            matched_evidence = copy.deepcopy(evidence)
            matched_evidence["query_match"] = True
            matched_evidence["question_id"] = item.get("question_id")
            linked_question = question_by_id.get(str(item.get("question_id") or ""))
            answer_shape_match = bool(linked_question) and _query_covers_answer_shape(
                item, linked_question)
            matched_evidence["answer_shape_match"] = answer_shape_match
            qualifies = ok and answer_shape_match
            if qualifies:
                qualified += 1
            item["status"] = "verified" if qualifies else "failed"
            item["readiness"] = "verified" if qualifies else "needs_fix"
            item.setdefault("verification_evidence", [])
            item["verification_evidence"].append(matched_evidence)
            latest_evidence = matched_evidence
            item["updated_at"] = _now()
            if item.get("question_id"):
                matched_question_ids.add(str(item["question_id"]))
            updated += 1
        for q in _list(self.data.get("competency_questions")):
            if not isinstance(q, dict):
                continue
            if str(q.get("id") or "") in matched_question_ids:
                matched_query = next((
                    item for item in _list(self.data.get("validation_queries"))
                    if isinstance(item, dict)
                    and str(item.get("question_id") or "") == str(q.get("id") or "")
                    and _status(item) == "verified"
                ), None)
                qualifies = matched_query is not None
                q["query_readiness"] = "verified" if qualifies else "needs_fix"
                q["verification_status"] = "verified" if qualifies else "failed"
                q["last_verification"] = copy.deepcopy(matched_evidence)
                q["updated_at"] = _now()
        if updated:
            self.touch()
        return {
            "updated": updated,
            "qualified": qualified,
            "evidence": latest_evidence,
        }

    def record_static_validation(self, result: dict[str, Any]) -> dict[str, Any]:
        """Record one bounded RDF handoff validation result.

        Only the latest run is retained. This prevents repeated button clicks
        from growing an unbounded monitoring history or duplicating review
        chores during a one-day workshop.
        """
        if not isinstance(result, dict):
            raise ValueError("validation result must be an object")
        status = str(result.get("status") or "fail").lower()
        if status not in {"pass", "warning", "fail"}:
            status = "fail"
        recorded = copy.deepcopy(result)
        recorded["status"] = status
        recorded.setdefault("scope", "static_handoff_validation")
        recorded.setdefault("validated_at", _now())
        recorded["freshness"] = "current"
        self.data["last_validation"] = recorded

        sparql = _dict(recorded.get("sparql"))
        sparql_status = sparql.get("status", "fail")
        sparql_ok = (
            sparql_status == "pass" and int(sparql.get("query_count") or 0) > 0
        )
        sparql_evidence = {
            "validated_at": recorded.get("validated_at"),
            "scope": recorded.get("scope"),
            "status": sparql_status,
            "query_count": sparql.get("query_count", 0),
            "executed": False,
            "report": _dict(recorded.get("reports")).get("validation_json"),
        }
        updated_queries = 0
        for item in _list(self.data.get("validation_queries")):
            if not isinstance(item, dict):
                continue
            if str(item.get("language", "")).lower() != "sparql":
                continue
            readiness = (
                "validated_static" if sparql_ok
                else ("needs_review" if sparql_status == "warning" else "needs_fix")
            )
            _system_change_item(item, {
                "status": readiness,
                "readiness": readiness,
                "last_static_validation": copy.deepcopy(sparql_evidence),
            }, "static_validation_recorded",
               "SPARQL seed structure was checked without executing SPARQL.")
            updated_queries += 1

        finding_text = (
            "Latest RDF handoff static validation failed; review the validation "
            "report before technical handoff."
        )
        action_text = (
            "Resolve the latest RDF/SPARQL/SHACL static validation failures and "
            "rerun the on-demand check once."
        )
        review_items = [
            item for item in _list(self.data.get("review_findings"))
            if isinstance(item, dict) and item.get("text") == finding_text
        ]
        action_items = [
            item for item in _list(self.data.get("action_items"))
            if isinstance(item, dict) and item.get("text") == action_text
        ]
        if status == "fail":
            if review_items:
                finding = review_items[0]
            else:
                finding = self.add_unique_item("review_findings", "finding", {
                    "text": finding_text,
                    "stage": "validation_handoff",
                    "source": "static_handoff_validation",
                })
            if action_items:
                action = action_items[0]
            else:
                action = self.add_unique_item("action_items", "action", {
                    "text": action_text,
                    "stage": "validation_handoff",
                    "source": "static_handoff_validation",
                    "owner": "operator",
                })
            for item in (finding, action):
                _system_change_item(item, {
                    "status": "open",
                    "validation_summary": recorded.get("summary"),
                    "validation_report": _dict(recorded.get("reports")).get(
                        "validation_markdown"),
                }, "static_validation_failed",
                   "The latest bounded static validation failed.")
                item.pop("resolved_at", None)
        elif status == "pass":
            for item in review_items + action_items:
                _system_change_item(item, {
                    "status": "resolved",
                    "resolved_at": _now(),
                }, "static_validation_resolved",
                   "A later bounded static validation no longer failed.")
        else:
            for item in review_items + action_items:
                _system_change_item(item, {
                    "status": "open",
                    "validation_summary": recorded.get("summary"),
                }, "static_validation_warning",
                   "A warning-only rerun does not resolve the prior validation failure.")

        self.touch()
        return {
            "status": status,
            "updated_queries": updated_queries,
            "latest_only": True,
        }

    def gates(self, context: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
        """Evaluate domain-neutral evidence quality, linkage, and decisions."""
        ctx = context or {}
        graph = _dict(ctx.get("graph"))
        gates: dict[str, dict[str, Any]] = {}

        stories = [item for item in _list(self.data.get("user_stories")) if _active(item)]
        high_stories = [item for item in stories if _high_priority(item)]
        complete_stories = [
            item for item in high_stories
            if not _has_merge_conflicts(item)
            and all(_meaningful_text(item, key) for key in (
                "actor", "goal", "decision", "success_metric", "scope"))
        ]
        gates["inception"] = _quality_gate([
            _check("inception.priority_story", bool(high_stories),
                   "at least one high-priority user story"),
            _check("inception.story_fields", len(complete_stories) == len(high_stories)
                   and bool(high_stories),
                   "actor, goal, decision, success metric, and one-day scope for every high-priority story",
                   {"complete_story_ids": [s.get("id") for s in complete_stories]}),
        ], {"user_stories": len(stories), "high_priority": len(high_stories)})

        claims = [
            item for item in _list(self.data.get("claims"))
            if _active(item) and item.get("stage") == "discovery"
            and _meaningful_text(item, "text") and not _has_merge_conflicts(item)
        ]
        valid_story_ids = {
            str(story.get("id")) for story in high_stories if story.get("id")
        }
        linked_claims = [
            item for item in claims
            if bool(_ids(item, "story_id", "story_ids") & valid_story_ids)
        ]
        defined_terms = [
            item for item in claims
            if _status(item) == "confirmed"
            and (_dict(item.get("definitions")) or _list(item.get("terms"))
                 or _list(item.get("glossary")))
        ]
        term_decisions = [
            item for collection in ("decisions", "review_findings")
            for item in _list(self.data.get(collection))
            if _active(item) and item.get("stage") == "discovery"
            and item.get("category") in {"terminology", "ambiguity"}
            and _status(item) in {"confirmed", "accepted", "resolved", "rejected"}
        ]
        terms_reviewed = bool(defined_terms or term_decisions)
        gates["discovery"] = _quality_gate([
            _check("discovery.narrative", bool(claims), "a discovery-stage domain narrative"),
            _check("discovery.goal_link", bool(linked_claims),
                   "a narrative explicitly linked to a priority story"),
            _check("discovery.terms", terms_reviewed,
                   "confirmed terms or an explicitly resolved ambiguity decision"),
        ], {"narrative_claims": len(claims), "linked_claims": len(linked_claims)})

        events = [item for item in _list(self.data.get("domain_events")) if _active(item)]
        complete_events = [
            item for item in events
            if not _has_merge_conflicts(item)
            and _meaningful_text(item, "name", "text")
            and _meaningful_text(item, "trigger")
            and _meaningful_text(item, "state_change")
            and _event_modeling_class(
                item.get("modeling_decision") or item.get("classification")
                or item.get("modeled_as"))
        ]
        incomplete_events = [
            item for item in events if item not in complete_events
        ]
        no_event_rationale = any(
            _active(item) and item.get("stage") == "event_discovery"
            and _has_text(item, "no_event_rationale", "rationale")
            for item in _list(self.data.get("decisions"))
        )
        unresolved_event = [
            item for item in _list(self.data.get("review_findings"))
            if _active(item) and item.get("category") == "event_modeling"
            and _status(item) in _PENDING_REVIEW_STATUSES
        ]
        gates["event_discovery"] = _quality_gate([
            _check("event.events", (bool(complete_events)
                   and not incomplete_events) or (not events and no_event_rationale),
                   "trigger, state change, and node/relation/property classification for every captured event, or an explicit no-event rationale"),
            _check("event.semantics", not unresolved_event,
                   "resolution of open event-modeling semantics",
                   {"open_finding_ids": [i.get("id") for i in unresolved_event]}),
        ], {"events": len(events), "complete_events": len(complete_events),
            "no_event_rationale": no_event_rationale})

        questions = [
            item for item in _list(self.data.get("competency_questions")) if _active(item)
        ]
        high_questions = [item for item in questions if _high_priority(item)]
        story_ids = {str(item.get("id")) for item in high_stories if item.get("id")}
        complete_questions = [
            item for item in high_questions
            if not _has_merge_conflicts(item)
            and _meaningful_text(item, "question", "text")
            and bool(_meaningful_values(
                item.get("expected_answer_shape") or item.get("answer_shape")))
            and bool(_ids(item, "story_id", "story_ids", "user_story_id") & story_ids)
        ]
        covered_story_ids = set().union(*[
            _ids(q, "story_id", "story_ids", "user_story_id") for q in complete_questions
        ]) if complete_questions else set()
        prioritized_questions = [
            item for item in questions
            if str(item.get("priority") or "").lower() in {
                "high", "medium", "low", "critical", "p0", "p1", "p2", "p3"
            }
        ]
        gates["story_to_question"] = _quality_gate([
            _check("question.priority", bool(high_questions),
                   "at least one high-priority competency question"),
            _check("question.answer_shape", len(complete_questions) == len(high_questions) and bool(high_questions),
                   "an expected answer shape and story link for every high-priority question"),
            _check("question.prioritization", len(prioritized_questions) == len(questions)
                   and bool(questions),
                   "an explicit workshop priority for every competency question"),
            _check("question.story_coverage", bool(story_ids) and story_ids <= covered_story_ids,
                   "competency-question coverage for every high-priority story",
                   {"uncovered_story_ids": sorted(story_ids - covered_story_ids)}),
        ], {"questions": len(questions), "high_priority": len(high_questions),
            "complete": len(complete_questions)})

        candidates = [item for item in _list(self.data.get("model_candidates")) if _active(item)]
        linked_candidates = [
            item for item in candidates
            if _candidate_has_valid_link(item, self.data)
        ]
        model_names = {str(item.get("name")) for item in candidates if item.get("name")}
        candidate_entity_names = {
            str(item.get("name")) for item in candidates
            if str(item.get("kind") or "").lower() in {
                "entity", "event", "event_node"
            } and item.get("name")
        }
        candidate_relation_names = {
            str(item.get("name")) for item in candidates
            if str(item.get("kind") or "").lower() == "relation"
            and item.get("name")
        }
        expected_names = {
            str(name) for question in high_questions
            for name in _list(question.get("expected_answer_shape") or question.get("answer_shape"))
            if name
        }
        graph_has_model = int(graph.get("entities") or 0) > 0 and int(graph.get("relations") or 0) > 0
        graph_names = {str(name) for name in ctx.get("entity_names") or []}
        graph_relation_names = {str(name) for name in ctx.get("relation_names") or []}
        tbox = _dict(ctx.get("tbox"))
        tbox_entities = _dict(tbox.get("entities"))
        tbox_relations = _dict(tbox.get("relations"))
        uncovered_shape = expected_names - (model_names | graph_names)
        untraced_graph_entities = graph_names - candidate_entity_names
        untraced_graph_relations = graph_relation_names - candidate_relation_names
        untraced_graph_types = untraced_graph_entities | untraced_graph_relations
        naming_conflicts = [item for item in candidates if _has_merge_conflicts(item)]
        incomplete_relations = [
            item for item in candidates
            if str(item.get("kind") or "").lower() == "relation"
            and not (_has_text(item, "src", "source_type")
                     and _has_text(item, "dst", "target_type"))
        ]
        known_entity_names = graph_names | {
            str(item.get("name")) for item in candidates
            if str(item.get("kind") or "").lower() in {
                "entity", "event", "event_node"
            } and item.get("name")
        }
        invalid_relation_endpoints = []
        for item in candidates:
            if str(item.get("kind") or "").lower() != "relation":
                continue
            src = str(item.get("src") or item.get("source_type") or "")
            dst = str(item.get("dst") or item.get("target_type") or "")
            actual = _dict(tbox_relations.get(str(item.get("name") or "")))
            if (src not in known_entity_names or dst not in known_entity_names
                    or actual and (
                        str(actual.get("src") or "") != src
                        or str(actual.get("dst") or "") != dst
                    )):
                invalid_relation_endpoints.append(item)
        question_patterns = []
        for question in high_questions:
            question_id = str(question.get("id") or "")
            expected = _meaningful_values(
                question.get("expected_answer_shape")
                or question.get("answer_shape"))
            expected_normalized = {_norm_value(name) for name in expected}
            linked = [
                item for item in candidates
                if question_id
                and question_id in _ids(item, "question_id", "question_ids")
            ]
            linked_by_name: dict[str, list[dict[str, Any]]] = {}
            for item in linked:
                if _meaningful_text(item, "name"):
                    linked_by_name.setdefault(
                        _norm_value(item.get("name")), []).append(item)
            linked_entity_names = {
                _norm_value(item.get("name"))
                for item in linked
                if str(item.get("kind") or "").lower() in {
                    "entity", "event", "event_node"
                } and _meaningful_text(item, "name")
            }
            linked_relations = [
                item for item in linked
                if str(item.get("kind") or "").lower() == "relation"
                and _norm_value(
                    item.get("src") or item.get("source_type"))
                in linked_entity_names
                and _norm_value(
                    item.get("dst") or item.get("target_type"))
                in linked_entity_names
            ]
            missing = [
                name for name in expected
                if not any(
                    _candidate_matches_tbox_kind(
                        item, name, tbox_entities, tbox_relations)
                    for item in linked_by_name.get(_norm_value(name), [])
                )
            ]
            relation_required = len(expected) >= 2
            pattern_adjacency: dict[str, set[str]] = {}
            for relation in linked_relations:
                relation_name = _norm_value(relation.get("name"))
                src = _norm_value(
                    relation.get("src") or relation.get("source_type"))
                dst = _norm_value(
                    relation.get("dst") or relation.get("target_type"))
                pattern_adjacency.setdefault(src, set()).add(dst)
                pattern_adjacency.setdefault(dst, set()).add(src)
                if relation_name:
                    pattern_adjacency.setdefault(relation_name, set()).update(
                        {src, dst})
                    pattern_adjacency.setdefault(src, set()).add(relation_name)
                    pattern_adjacency.setdefault(dst, set()).add(relation_name)
            connected_names = _connected_names(
                expected_normalized, pattern_adjacency,
                _norm_value(expected[0]) if expected else "")
            disconnected = [
                name for name in expected
                if _norm_value(name) not in connected_names
            ]
            relation_pattern_ok = (
                not relation_required
                or bool(linked_relations)
                and not disconnected
            )
            question_patterns.append({
                "question_id": question_id,
                "expected_elements": expected,
                "linked_candidate_ids": [
                    item.get("id") for item in linked if item.get("id")
                ],
                "missing_elements": missing,
                "relation_required": relation_required,
                "disconnected_elements": disconnected,
                "linked_relation_ids": [
                    item.get("id") for item in linked_relations if item.get("id")
                ],
                "status": "pass" if (
                    question_id and expected and not missing
                    and relation_pattern_ok
                ) else "fail",
            })
        invalid_question_patterns = [
            pattern for pattern in question_patterns
            if pattern["status"] != "pass"
        ]
        duplicate_pairs = [
            (left, right)
            for index, left in enumerate(candidates)
            for right in candidates[index + 1:]
            if _similar_model_names(left.get("name"), right.get("name"))
        ]
        unresolved_duplicates = [
            (left, right) for left, right in duplicate_pairs
            if not _duplicate_pair_reviewed(
                left, right, self.data.get("review_findings"),
                self.data.get("action_items"))
        ]
        gates["model_synthesis"] = _quality_gate([
            _check("model.structure", bool(candidates) and graph_has_model,
                   "candidate model elements plus a non-empty T-Box with entities and relations"),
            _check("model.relations", not incomplete_relations,
                   "source and target types for every relation candidate",
                   {"incomplete_relation_ids": [i.get("id") for i in incomplete_relations]}),
            _check("model.relation_endpoints", not invalid_relation_endpoints,
                   "relation endpoints that reference known entities and match the current T-Box",
                   {"invalid_relation_ids": [
                       item.get("id") for item in invalid_relation_endpoints
                   ]}),
            _check("model.traceability", len(linked_candidates) == len(candidates) and bool(candidates),
                   "a story, event, question, or data-source link for every model candidate"),
            _check("model.graph_traceability", not untraced_graph_types and graph_has_model,
                   "a traceable, kind-compatible model candidate for every T-Box entity and relation",
                   {"untraced_tbox_entities": sorted(untraced_graph_entities),
                    "untraced_tbox_relations": sorted(untraced_graph_relations)}),
            _check("model.question_coverage", not uncovered_shape and bool(expected_names),
                   "candidate model coverage for every expected answer-shape element",
                   {"uncovered_elements": sorted(uncovered_shape)}),
            _check("model.question_patterns",
                   bool(question_patterns) and not invalid_question_patterns,
                   "a question-linked candidate graph pattern for every high-priority question",
                   {"questions": question_patterns}),
            _check("model.naming", not naming_conflicts,
                   "explicit resolution of duplicate or naming conflicts",
                   {"conflict_ids": [item.get("id") for item in naming_conflicts]}),
            _check("model.duplicates", not unresolved_duplicates,
                   "explicit review of every similar or duplicate model concept",
                   {"unreviewed_pairs": [
                       [left.get("id"), right.get("id")]
                       for left, right in unresolved_duplicates
                   ]}),
        ], {"model_candidates": len(candidates), "linked": len(linked_candidates),
            "entities": graph.get("entities", 0), "relations": graph.get("relations", 0)})

        sources = [item for item in _list(self.data.get("data_sources")) if _active(item)]
        mappings = [item for item in _list(self.data.get("field_mappings")) if _active(item)]
        source_names = {str(item.get("name")) for item in sources if item.get("name")}
        source_fields = {
            str(item.get("name")): {
                str(field) for field in _dict(item.get("fields"))
            }
            for item in sources if item.get("name")
        }
        valid_mapping_targets = model_names | graph_names | graph_relation_names
        target_properties: dict[str, set[str]] = {}
        for name, definition in {**tbox_entities, **tbox_relations}.items():
            target_properties[str(name)] = {
                str(prop) for prop in _dict(_dict(definition).get("properties"))
            }
        for candidate in candidates:
            if candidate.get("name") and isinstance(candidate.get("properties"), dict):
                target_properties.setdefault(str(candidate["name"]), set()).update(
                    str(prop) for prop in candidate["properties"]
                )
        actionable_statuses = {"available", "partial", "missing", "derived", "unknown"}
        well_formed_mappings = [
            item for item in mappings
            if not _has_merge_conflicts(item)
            and _has_text(item, "source") and _has_text(item, "source_field")
            and str(item.get("source")) in source_names
            and (not source_fields.get(str(item.get("source")))
                 or str(item.get("source_field")) in source_fields[
                     str(item.get("source"))])
            and _has_text(item, "target") and not str(item.get("target", "")).startswith("TBD.")
            and _mapping_target_valid(
                item.get("target"), valid_mapping_targets, target_properties)
            and _readiness_status(item.get("status") or item.get("readiness")) in actionable_statuses
        ]
        unresolved_mappings = [
            item for item in mappings
            if _readiness_status(item.get("status") or item.get("readiness")) in {"missing", "unknown"}
        ]
        mapping_actions = [
            item for item in _list(self.data.get("action_items"))
            if _active(item) and not _has_merge_conflicts(item)
            and _meaningful_text(item, "owner")
            and _meaningful_text(item, "text", "title", "description")
            and _status(item) in {"open", "accepted", "confirmed", "in_progress"}
        ]
        mapped_action_ids = set().union(*[
            _ids(item, "mapping_id", "mapping_ids", "target_id", "target_ids")
            for item in mapping_actions
        ]) if mapping_actions else set()
        unresolved_without_action = [
            item for item in unresolved_mappings if str(item.get("id")) not in mapped_action_ids
        ]
        mapped_targets = {
            str(item.get("target") or "").split(".", 1)[0]
            for item in mappings if item.get("target")
        }
        uncovered_model_data = expected_names - mapped_targets
        source_quality = all(
            not _has_merge_conflicts(item)
            and _meaningful_text(item, "owner")
            and _meaningful_text(item, "freshness")
            for item in sources
        ) if sources else False
        gates["data_grounding"] = _quality_gate([
            _check("data.sources", bool(sources), "at least one identified data source"),
            _check("data.mappings", len(well_formed_mappings) == len(mappings) and bool(mappings),
                   "source, field, concrete target, and readiness status for every mapping"),
            _check("data.source_metadata", source_quality,
                   "owner and freshness metadata for each data source"),
            _check("data.model_coverage", not uncovered_model_data and bool(expected_names),
                   "a readiness mapping for every high-priority answer-shape model element",
                   {"unmapped_elements": sorted(uncovered_model_data)}),
            _check("data.gap_actions", not unresolved_without_action,
                   "a linked action item for every missing or unknown mapping",
                   {"mapping_ids_without_action": [item.get("id") for item in unresolved_without_action]}),
        ], {"data_sources": len(sources), "field_mappings": len(mappings),
            "well_formed_mappings": len(well_formed_mappings)})

        review_items = [
            item for collection in ("review_findings", "assumptions", "contradictions", "risks")
            for item in _list(self.data.get(collection)) if _active(item)
        ]
        pending_critical = [
            item for item in review_items
            if str(item.get("severity") or "").lower() == "critical"
            and _status(item) not in {"resolved", "rejected", "out_of_scope"}
        ]
        pending_high = [
            item for item in review_items
            if str(item.get("severity") or "").lower() == "high"
            and not _review_item_disposed(item, self.data.get("action_items"))
        ]
        pending_automatic = [
            item for item in review_items
            if item.get("source") == "automatic_adversarial_review"
            and not _review_item_disposed(item, self.data.get("action_items"))
        ]
        review_runs = _list(self.data.get("review_runs"))
        latest_review = _dict(review_runs[-1]) if review_runs else {}
        assessed = set(latest_review.get("categories_assessed") or [])
        review_current = bool(latest_review) and latest_review.get(
            "source_fingerprint") == _review_source_fingerprint(self.data, ctx)
        material_review = int(latest_review.get("reviewed_evidence_count") or 0) > 0
        gates["adversarial_review"] = _quality_gate([
            _check("review.executed", bool(latest_review) and material_review,
                   "an explicit adversarial review run over material workshop evidence"),
            _check("review.freshness", review_current,
                   "an adversarial review current with the latest workshop evidence"),
            _check("review.coverage", REVIEW_CATEGORIES <= assessed,
                   "review coverage for ambiguity, contradiction, causality, event modeling, over-modeling, and sensitivity",
                   {"missing_categories": sorted(REVIEW_CATEGORIES - assessed)}),
            _check("review.critical", not pending_critical,
                   "resolution or explicit rejection of every critical contradiction/finding/risk",
                   {"open_ids": [item.get("id") for item in pending_critical]}),
            _check("review.high", not pending_high,
                   "acceptance as an owned action, resolution, or rejection of every high-severity review item",
                   {"open_ids": [item.get("id") for item in pending_high]}),
            _check("review.decisions", not pending_automatic,
                   "an explicit accept, reject, or resolve decision for every automatically generated review item",
                   {"open_ids": [item.get("id") for item in pending_automatic]}),
        ], {"review_items": len(review_items), "review_runs": len(review_runs),
            "pending_critical": len(pending_critical), "pending_high": len(pending_high),
            "pending_automatic": len(pending_automatic)})

        current_source_fingerprint = ctx.get("query_source_fingerprint")
        verified_question_ids = _verified_question_ids(
            self.data.get("validation_queries"), high_questions,
            current_source_fingerprint)
        high_question_ids = {str(q.get("id")) for q in high_questions if q.get("id")}
        unverified_question_ids = high_question_ids - verified_question_ids
        action_items = [item for item in _list(self.data.get("action_items")) if _active(item)]
        owned_actions = [
            item for item in action_items
            if not _has_merge_conflicts(item)
            and _meaningful_text(item, "owner")
            and _meaningful_text(item, "text", "title", "description")
            and _status(item) in {"open", "accepted", "confirmed", "in_progress"}
        ]
        last_validation = _dict(self.data.get("last_validation"))
        validation_freshness = self._validation_freshness(ctx)
        validation_requested = bool(last_validation)
        static_validation_ok = (
            not validation_requested
            or last_validation.get("status") == "pass"
            and validation_freshness == "current"
            and int(graph.get("entities") or 0) > 0
            and int(graph.get("relations") or 0) > 0
        )
        open_validation_actions = [
            item for item in action_items
            if item.get("source") == "static_handoff_validation"
            and _status(item) not in _TERMINAL_REVIEW_STATUSES
        ]
        manifest = _dict(self.data.get("handoff_manifest"))
        validation_bundle_aligned = (
            not validation_requested
            or bool(manifest.get("rdf_source_fingerprint"))
            and manifest.get("rdf_source_fingerprint")
            == last_validation.get("source_fingerprint")
        )
        current_handoff_fingerprint = ctx.get("handoff_source_fingerprint")
        manifest_freshness = (
            "not_generated" if not manifest
            else "current" if manifest.get("source_fingerprint")
            and manifest.get("source_fingerprint") == current_handoff_fingerprint
            else "stale"
        )
        manifest_artifacts = _dict(manifest.get("artifacts"))
        missing_manifest_artifacts = sorted(
            key for key in REQUIRED_HANDOFF_ARTIFACTS
            if not manifest_artifacts.get(key)
        )
        manifest_files_valid = bool(ctx.get("handoff_manifest_files_valid", True))
        transition_history = _list(self.data.get("transition_history"))
        sequential_arrival = _sequential_arrival_complete(
            self.data.get("current_stage"), transition_history)
        gates["validation_handoff"] = _quality_gate([
            _check("handoff.stage",
                   sequential_arrival,
                   "sequential arrival at the Validation and Handoff stage",
                   {"current_stage": self.data.get("current_stage"),
                    "transition_count": len(transition_history),
                    "expected_transition_count": len(STAGES) - 1}),
            _check("handoff.prior_gates", all(
                gates[name]["status"] == "pass" for name in STAGES[:-1]),
                "successful completion of every preceding workshop gate",
                {"incomplete_gates": [
                    name for name in STAGES[:-1]
                    if gates[name]["status"] != "pass"
                ]}),
            _check("handoff.model", int(graph.get("entities") or 0) > 0
                   and int(graph.get("relations") or 0) > 0,
                   "a non-empty current T-Box for handoff"),
            _check("handoff.query_coverage", bool(high_question_ids) and not unverified_question_ids,
                   "successful matching openCypher execution evidence for every high-priority competency question",
                   {"unverified_question_ids": sorted(unverified_question_ids)}),
            _check("handoff.actions", bool(owned_actions),
                   "at least one owner-tagged handoff action item"),
            _check("handoff.artifacts", manifest.get("status") == "complete"
                   and manifest_freshness == "current"
                   and not missing_manifest_artifacts and manifest_files_valid,
                   "a current generated report, snapshot, Neptune package, and RDF handoff bundle",
                   {"status": manifest.get("status", "not_generated"),
                    "freshness": manifest_freshness,
                    "missing_artifacts": missing_manifest_artifacts,
                    "files_valid": manifest_files_valid}),
            _check("handoff.static_validation", static_validation_ok
                   and validation_bundle_aligned,
                   "a current PASS static validation of the same RDF inputs packaged for handoff when validation was requested; warnings, base-IRI drift, and empty models do not qualify",
                   {"requested": validation_requested,
                    "status": last_validation.get("status", "not_run"),
                    "freshness": validation_freshness,
                    "validated_source_fingerprint": last_validation.get(
                        "source_fingerprint"),
                    "packaged_rdf_source_fingerprint": manifest.get(
                        "rdf_source_fingerprint"),
                    "bundle_aligned": validation_bundle_aligned}),
            _check("handoff.validation_actions", not open_validation_actions,
                   "resolution of RDF static-validation failure actions",
                   {"open_action_ids": [item.get("id") for item in open_validation_actions]}),
        ], {"high_priority_questions": len(high_question_ids),
            "verified_question_ids": sorted(verified_question_ids),
            "verification_source_fingerprint": current_source_fingerprint,
            "owned_action_items": len(owned_actions),
            "handoff_manifest_freshness": manifest_freshness,
            "handoff_source_fingerprint": current_handoff_fingerprint,
            "rdf_static_validation": last_validation.get("status", "not_run"),
            "sparql_executed": False, "shacl_engine_executed": False})
        return gates


def _check(check_id: str, passed: bool, requirement: str,
           evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "requirement": requirement,
        "evidence": evidence or {},
    }


def _quality_gate(checks: list[dict[str, Any]],
                  evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = [
        str(check.get("requirement")) for check in checks
        if check.get("status") != "pass"
    ]
    passed = len(checks) - len(missing)
    status = "pass" if not missing else ("partial" if passed else "fail")
    return {
        "status": status,
        "missing": missing,
        "evidence": evidence or {},
        "checks": checks,
    }


def _sequential_arrival_complete(current_stage: Any, history: Any) -> bool:
    """Prove the canonical stage chain, including audited forced next steps."""
    if current_stage != STAGES[-1]:
        return False
    transitions = _list(history)
    if len(transitions) != len(STAGES) - 1:
        return False
    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            return False
        if (transition.get("from") != STAGES[index]
                or transition.get("to") != STAGES[index + 1]
                or not _meaningful_text(transition, "actor")
                or not _meaningful_text(transition, "at")):
            return False
        if transition.get("forced") and not _meaningful_text(
                transition, "reason"):
            return False
    return True


def _candidate_has_link(item: dict[str, Any]) -> bool:
    return bool(_ids(
        item, "story_id", "story_ids", "event_id", "event_ids",
        "question_id", "question_ids", "data_source_id", "data_source_ids",
    ))


def _mapping_target_valid(target: Any, valid_names: set[str],
                          properties: dict[str, set[str]]) -> bool:
    value = str(target or "").strip()
    if not value or value.startswith("TBD."):
        return False
    parts = value.split(".", 1)
    if parts[0] not in valid_names:
        return False
    if len(parts) == 1:
        return True
    return parts[0] not in properties or parts[1] in properties[parts[0]]


def _candidate_has_valid_link(item: dict[str, Any], state: dict[str, Any]) -> bool:
    references = {
        "story": (_ids(item, "story_id", "story_ids"), "user_stories"),
        "event": (_ids(item, "event_id", "event_ids"), "domain_events"),
        "question": (_ids(item, "question_id", "question_ids"),
                     "competency_questions"),
        "data": (_ids(item, "data_source_id", "data_source_ids"), "data_sources"),
    }
    for ids, collection in references.values():
        existing = {
            str(value.get("id")) for value in _list(state.get(collection))
            if _active(value) and value.get("id")
        }
        if ids & existing:
            return True
    return False


def _candidate_matches_tbox_kind(item: dict[str, Any], name: str,
                                 tbox_entities: dict[str, Any],
                                 tbox_relations: dict[str, Any]) -> bool:
    """Require a question-linked candidate to match the current T-Box kind."""
    kind = str(item.get("kind") or "").lower()
    normalized = _norm_value(name)
    if normalized in {_norm_value(value) for value in tbox_entities}:
        return kind in {"entity", "event", "event_node"}
    if normalized in {_norm_value(value) for value in tbox_relations}:
        return kind == "relation"
    return kind in {"entity", "event", "event_node", "relation"}


def _connected_names(required: set[str], adjacency: dict[str, set[str]],
                     start: str = "") -> set[str]:
    """Return required model names reachable in one relation pattern component."""
    if not required:
        return set()
    start = start if start in required else sorted(required)[0]
    visited: set[str] = set()
    pending = [start]
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacency.get(current, set()) - visited)
    return required & visited


def _review_item_disposed(item: dict[str, Any], action_items: Any) -> bool:
    if _status(item) in {"resolved", "rejected", "out_of_scope"}:
        return True
    if _status(item) not in {"accepted", "confirmed"}:
        return False
    severity = str(item.get("severity") or "").lower()
    if severity == "critical":
        return False
    if severity not in {"high", "critical"}:
        return True
    if _status(item) == "confirmed":
        return False
    linked = _ids(item, "linked_action_id", "linked_action_ids")
    return any(
        isinstance(action, dict) and str(action.get("id")) in linked
        and not _has_merge_conflicts(action)
        and _meaningful_text(action, "owner")
        and _meaningful_text(action, "text", "title", "description")
        and _status(action) not in {"rejected", "out_of_scope"}
        for action in _list(action_items)
    )


def _review_evidence_count(state: dict[str, Any]) -> int:
    return sum(
        len(_list(state.get(collection)))
        for collection in (
            "claims", "user_stories", "domain_events", "competency_questions",
            "model_candidates", "data_sources", "field_mappings",
        )
    )


def _review_source_fingerprint(state: dict[str, Any],
                               context: dict[str, Any] | None = None) -> str:
    payload = {
        collection: [
            {
                key: value for key, value in item.items()
                if key not in {
                    "history", "created_at", "updated_at",
                    *_VIEW_ONLY_ITEM_FIELDS,
                }
            }
            for item in _list(state.get(collection)) if isinstance(item, dict)
        ]
        for collection in (
            "claims", "user_stories", "domain_events", "competency_questions",
            "model_candidates", "data_sources", "field_mappings",
        )
    }
    ctx = context or {}
    payload["graph"] = {
        "summary": _dict(ctx.get("graph")),
        "entity_names": sorted(str(value) for value in ctx.get("entity_names") or []),
        "relation_names": sorted(str(value) for value in ctx.get("relation_names") or []),
        "schema": _dict(ctx.get("tbox")),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _handoff_source_fingerprint(state: dict[str, Any],
                                graph_fingerprint: str = "") -> str:
    payload = {
        "graph_fingerprint": graph_fingerprint or "",
        "version": state.get("version"),
        "current_stage": state.get("current_stage"),
        "language": state.get("language"),
        "scope": state.get("scope"),
    }
    payload.update({
        collection: [
            {
                key: value for key, value in item.items()
                if key not in {"history", "created_at", "updated_at"}
            }
            for item in _list(state.get(collection)) if isinstance(item, dict)
        ]
        for collection in WORKFLOW_COLLECTIONS
    })
    payload["last_validation"] = {
        key: copy.deepcopy(value)
        for key, value in _dict(state.get("last_validation")).items()
        if key not in _VIEW_ONLY_VALIDATION_FIELDS
    }
    payload["review_runs"] = copy.deepcopy(_list(state.get("review_runs")))
    payload["transition_history"] = copy.deepcopy(
        _list(state.get("transition_history")))
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _query_source_fingerprint(tbox: Any, snapshot: Any,
                              state: dict[str, Any]) -> str:
    snap = _dict(snapshot)
    payload = {
        "tbox": _dict(tbox),
        "snapshot": {
            "nodes": _list(snap.get("nodes")),
            "edges": _list(snap.get("edges")),
        },
        "competency_questions": [
            {
                key: value for key, value in item.items()
                if key in {
                    "id", "question", "text", "expected_answer_shape",
                    "answer_shape", "priority", "story_id", "story_ids",
                }
            }
            for item in _list(state.get("competency_questions"))
            if isinstance(item, dict)
        ],
        "open_cypher_queries": [
            {
                key: value for key, value in item.items()
                if key in {"id", "question_id", "question", "language", "query"}
            }
            for item in _list(state.get("validation_queries"))
            if isinstance(item, dict)
            and str(item.get("language") or "").lower() == "opencypher"
        ],
        "model_candidates": [
            {
                key: value for key, value in item.items()
                if key in {
                    "id", "kind", "name", "src", "dst", "source_type",
                    "target_type", "properties", "primary_key", "status",
                    "question_id", "question_ids", "story_id", "story_ids",
                    "event_id", "event_ids", "data_source_id", "data_source_ids",
                }
            }
            for item in _list(state.get("model_candidates"))
            if isinstance(item, dict)
        ],
        "data_sources": [
            {
                key: value for key, value in item.items()
                if key in {
                    "id", "name", "type", "fields", "owner", "freshness",
                    "status", "sensitivity",
                }
            }
            for item in _list(state.get("data_sources"))
            if isinstance(item, dict)
        ],
        "field_mappings": [
            {
                key: value for key, value in item.items()
                if key in {
                    "id", "source", "source_field", "target", "status",
                    "readiness",
                }
            }
            for item in _list(state.get("field_mappings"))
            if isinstance(item, dict)
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _candidate_question_links(item: dict[str, Any], questions: Any) -> list[str]:
    name = str(item.get("name") or "").strip().lower()
    if not name:
        return []
    linked = []
    for question in _list(questions):
        if not _active(question) or not question.get("id"):
            continue
        shape = {
            str(value).strip().lower()
            for value in _list(question.get("expected_answer_shape") or question.get("answer_shape"))
        }
        if name in shape:
            linked.append(str(question["id"]))
    return linked


def _verified_question_ids(validation_queries: Any,
                           high_questions: list[dict[str, Any]],
                           current_source_fingerprint: Any = None) -> set[str]:
    high_ids = {str(item.get("id")) for item in high_questions if item.get("id")}
    verified: set[str] = set()
    for query in _list(validation_queries):
        if not isinstance(query, dict):
            continue
        if str(query.get("language") or "").strip().lower() != "opencypher":
            continue
        question_id = str(query.get("question_id") or "")
        if question_id not in high_ids or _status(query) != "verified":
            continue
        question_item = next(
            (item for item in high_questions
             if str(item.get("id")) == question_id), None)
        if (_has_merge_conflicts(query) or question_item is None
                or not _query_covers_answer_shape(query, question_item)):
            continue
        evidence = _list(query.get("verification_evidence"))
        if any(
            bool(item.get("ok")) and item.get("query_match") is True
            and item.get("answer_shape_match") is not False
            and bool(current_source_fingerprint)
            and item.get("source_fingerprint") == current_source_fingerprint
            for item in evidence if isinstance(item, dict)
        ):
            verified.add(question_id)
    return verified


def _query_covers_answer_shape(query: dict[str, Any],
                               question: dict[str, Any]) -> bool:
    cypher = _strip_cypher_comments_and_strings(str(query.get("query") or ""))
    if not re.search(r"\bMATCH\b", cypher, re.I) or not re.search(
            r"\bRETURN\b", cypher, re.I):
        return False
    shape = [
        str(value) for value in _list(
            question.get("expected_answer_shape") or question.get("answer_shape"))
        if str(value).strip()
    ]
    if not shape:
        return False

    # A label name appearing anywhere in a query is not answer evidence. Build a
    # small, deliberately conservative map of MATCH-bound node/relationship
    # variables and require the variable for every expected label to be returned.
    # This rejects seeds such as `MATCH (n) WITH n AS Product RETURN 1` and
    # `MATCH (p:Product) RETURN 1`, without pretending to be a full Cypher parser.
    label_variables: dict[str, set[str]] = {}
    for pattern in (r"\(([^()]*)\)", r"\[([^\[\]]*)\]"):
        for match in re.finditer(pattern, cypher):
            header = match.group(1).split("{", 1)[0]
            variable_match = re.match(
                r"\s*`?([A-Za-z_][A-Za-z0-9_]*)`?", header)
            variable = variable_match.group(1) if variable_match else ""
            if not variable or header.lstrip().startswith(":"):
                continue
            for label in re.findall(
                    r":\s*`?([A-Za-z_][A-Za-z0-9_]*)`?", header):
                label_variables.setdefault(label.lower(), set()).add(
                    variable.lower())

    return_matches = list(re.finditer(r"\bRETURN\b", cypher, re.I))
    if not return_matches:
        return False
    return_clause = cypher[return_matches[-1].end():]
    return_clause = re.split(
        r"\b(?:ORDER\s+BY|SKIP|LIMIT|UNION)\b", return_clause,
        maxsplit=1, flags=re.I)[0]
    if re.search(r"(^|,)\s*\*\s*(,|$)", return_clause):
        returned_variables = {
            variable for variables in label_variables.values()
            for variable in variables
        }
    else:
        returned_variables: set[str] = set()
        for expression in _split_top_level_commas(return_clause):
            expression = re.sub(
                r"\bAS\s+`?[A-Za-z_][A-Za-z0-9_]*`?\s*$", "",
                expression, flags=re.I)
            returned_variables.update(
                token.lower() for token in re.findall(
                    r"`?([A-Za-z_][A-Za-z0-9_]*)`?", expression)
            )

    covered_variables = {
        name.lower(): label_variables.get(name.lower(), set()) & returned_variables
        for name in shape
    }
    if not all(covered_variables.values()):
        return False
    if len(shape) < 2:
        return True

    # A comma-separated Cartesian MATCH can return all requested labels without
    # answering their relationship. Require the returned answer variables to be
    # part of one explicit relationship pattern. This remains intentionally
    # conservative; complex seeds can be revised into an auditable connected
    # pattern instead of being treated as semantically proven by a regex.
    answer_variables = set().union(*covered_variables.values())
    adjacency: dict[str, set[str]] = {}
    relation_pattern = re.compile(
        r"(?=\(\s*`?([A-Za-z_][A-Za-z0-9_]*)`?[^()]*\)\s*"
        r"(?:<-|-)\s*\[[^\[\]]*\]\s*(?:->|-)\s*"
        r"\(\s*`?([A-Za-z_][A-Za-z0-9_]*)`?[^()]*\))",
        re.I)
    for match in relation_pattern.finditer(cypher):
        left, right = match.group(1).lower(), match.group(2).lower()
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
    return answer_variables <= _reachable_variables(answer_variables, adjacency)


def _reachable_variables(required: set[str],
                         adjacency: dict[str, set[str]]) -> set[str]:
    if not required:
        return set()
    start = next(iter(required))
    visited: set[str] = set()
    pending = [start]
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacency.get(current, set()) - visited)
    return visited


def _split_top_level_commas(value: str) -> list[str]:
    """Split a scrubbed expression list without splitting nested function calls."""
    parts: list[str] = []
    start = 0
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())
    for index, char in enumerate(value):
        if char in pairs:
            depth += 1
        elif char in closers and depth:
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def _strip_cypher_comments_and_strings(query: str) -> str:
    query = re.sub(r"/\*[\s\S]*?\*/", " ", query)
    query = re.sub(r"//[^\n\r]*|--[^\n\r]*", " ", query)
    query = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", " ", query)
    return query


def _review_finding(category: str, severity: str, text: str, stage: str,
                    evidence_ids: list[Any]) -> dict[str, Any]:
    return {
        "text": text,
        "category": category,
        "severity": severity,
        "status": "open",
        "stage": stage,
        "evidence_ids": [str(value) for value in evidence_ids if value],
        "source": "automatic_adversarial_review",
    }


def _claims_conflict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if _status(left) == "conflicting" or _status(right) == "conflicting":
        return bool(_ids(left, "conflicts_with", "conflict_ids") & {
            str(right.get("id"))
        } or _ids(right, "conflicts_with", "conflict_ids") & {
            str(left.get("id"))
        })
    left_subject = _norm_value(left.get("subject") or left.get("term"))
    right_subject = _norm_value(right.get("subject") or right.get("term"))
    left_value = _norm_value(left.get("value") or left.get("definition"))
    right_value = _norm_value(right.get("value") or right.get("definition"))
    return bool(
        left_subject and left_subject == right_subject
        and left_value and right_value and left_value != right_value
    )


def _similar_model_names(left: Any, right: Any) -> bool:
    def normalized(value: Any) -> str:
        raw = re.sub(r"[^a-z0-9]", "", str(value or "").lower())
        for suffix in ("entity", "record", "object", "data", "type"):
            if raw.endswith(suffix) and len(raw) > len(suffix) + 2:
                raw = raw[:-len(suffix)]
        return raw

    a, b = normalized(left), normalized(right)
    return bool(a and b and (a == b or (min(len(a), len(b)) >= 5 and (a in b or b in a))))


def _duplicate_pair_reviewed(left: dict[str, Any], right: dict[str, Any],
                             findings: Any, action_items: Any) -> bool:
    pair = {str(left.get("id")), str(right.get("id"))}
    for item in [*_list(findings), *_list(action_items)]:
        if not isinstance(item, dict) or item.get("category") not in {
            "duplicate", "over_modeling", "naming"
        }:
            continue
        if not pair <= _ids(item, "evidence_id", "evidence_ids", "model_ids"):
            continue
        if _review_item_disposed(item, action_items):
            return True
    return False


def _query_matches(item: dict[str, Any], question: str, cypher: str) -> bool:
    if not cypher or _norm_query(item.get("query")) != _norm_query(cypher):
        return False
    if (not question or not _norm_value(item.get("question"))
            or _norm_value(item.get("question")) != _norm_value(question)):
        return False
    return True


def infer_workflow_items(text: str, stage: str,
                         state: dict[str, Any] | None = None,
                         context: dict[str, Any] | None = None) -> dict[str, list[dict]]:
    """Infer conservative AI-ODLC evidence objects from a user answer."""
    state = state or {}
    context = context or {}
    out: dict[str, list[dict]] = {k: [] for k in WORKFLOW_COLLECTIONS}
    text = (text or "").strip()
    if not text:
        return out

    _extend_items(out, _extract_structured_items(text))
    facts = _key_values(text)

    if not out["user_stories"]:
        story = _story_from_facts(facts)
        if story:
            out["user_stories"].append(story)
        elif stage == "inception":
            inferred = _infer_story(text)
            if inferred:
                out["user_stories"].append(inferred)

    if facts.get("decision"):
        out["decisions"].append({"text": facts["decision"], "status": "candidate"})

    if not out["competency_questions"]:
        for question in _questions_from_text(text):
            out["competency_questions"].append({
                "question": question,
                "priority": "high" if stage == "story_to_question" else "medium",
                "expected_answer_shape": _answer_shape(question, state, context),
                "status": "candidate",
            })

    for event in _events_from_text(text, stage):
        out["domain_events"].append(event)

    _extend_items(out, _data_items_from_text(text, facts, stage))
    _extend_items(out, _model_items_from_facts(facts, text, stage))
    _extend_items(out, _review_items_from_text(text, stage))
    if not out["rdf_decisions"]:
        _extend_items(out, _rdf_items_from_text(text))
    return {k: v for k, v in out.items() if v}


def summarize_extraction(added: dict[str, list[dict[str, Any]]]) -> str:
    parts = []
    labels = {
        "user_stories": "stories",
        "domain_events": "events",
        "competency_questions": "questions",
        "model_candidates": "model candidates",
        "data_sources": "data sources",
        "field_mappings": "field mappings",
        "risks": "risks",
        "assumptions": "assumptions",
        "action_items": "actions",
        "validation_queries": "query candidates",
        "rdf_decisions": "RDF notes",
    }
    for key, label in labels.items():
        count = len(added.get(key) or [])
        if count:
            parts.append(f"{count} {label}")
    return ", ".join(parts) if parts else "claim captured; more structure needed"


def _merge_extracted(generated: dict[str, list[dict]],
                     extracted: dict[str, Any] | None) -> dict[str, list[dict]]:
    out = {k: list(v) for k, v in (generated or {}).items()}
    _extend_items(out, _normalize_structured_payload(extracted))
    return {k: v for k, v in out.items() if v}


def _extend_items(target: dict[str, list[dict]], extra: dict[str, list[dict]]) -> None:
    for collection, items in (extra or {}).items():
        if collection not in WORKFLOW_COLLECTIONS:
            continue
        target.setdefault(collection, [])
        for item in items or []:
            if isinstance(item, dict):
                target[collection].append(item)


def _extract_structured_items(text: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for payload in _json_payloads(text):
        _extend_items(out, _normalize_structured_payload(payload))
    return out


def _json_payloads(text: str) -> list[Any]:
    candidates = []
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        candidates.append(stripped)
    candidates.extend(
        match.group(1)
        for match in re.finditer(r"~~~(?:json)?\s*([\s\S]*?)~~~", text, re.I)
    )
    if "{" in text and "}" in text:
        candidates.append(text[text.find("{"): text.rfind("}") + 1])
    parsed = []
    seen = set()
    for raw in candidates:
        raw = raw.strip()
        if not raw or raw in seen:
            continue
        seen.add(raw)
        try:
            parsed.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return parsed


def _normalize_structured_payload(payload: Any) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {k: [] for k in WORKFLOW_COLLECTIONS}
    if isinstance(payload, list):
        payload = {"items": payload}
    if not isinstance(payload, dict):
        return {}

    for key, value in payload.items():
        norm_key = str(key).strip().lower().replace("-", "_")
        collection = _JSON_COLLECTION_ALIASES.get(norm_key)
        if collection:
            for item in _as_items(value):
                out[collection].append(item)
            continue

        if norm_key in {"entity_types", "entities"}:
            for item in _as_items(value):
                name = item.get("name") or item.get("entity") or item.get("type")
                if name:
                    out["model_candidates"].append({
                        "kind": "entity",
                        "name": str(name),
                        "properties": item.get("properties") or item.get("fields") or {},
                        "primary_key": item.get("primary_key") or item.get("key"),
                        "status": item.get("status", "candidate"),
                    })
            continue

        if norm_key in {"relations", "relation_types"}:
            for item in _as_items(value):
                name = item.get("name") or item.get("relation") or item.get("type")
                if name:
                    out["model_candidates"].append({
                        "kind": "relation",
                        "name": str(name),
                        "src": item.get("src") or item.get("source"),
                        "dst": item.get("dst") or item.get("target"),
                        "cardinality": item.get("cardinality"),
                        "properties": item.get("properties") or {},
                        "status": item.get("status", "candidate"),
                    })
            continue

        if norm_key in {"tables", "schemas"}:
            _extend_items(out, _tables_to_sources(value))
            continue

        if norm_key == "items":
            for item in _as_items(value):
                kind = item.get("kind")
                if kind in _JSON_COLLECTION_ALIASES:
                    out[_JSON_COLLECTION_ALIASES[kind]].append(item)

    return {k: v for k, v in out.items() if v}


def _as_items(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, dict):
                items.append(item)
            elif item not in (None, ""):
                items.append({"text": str(item)})
        return items
    if value not in (None, ""):
        return [{"text": str(value)}]
    return []


def _tables_to_sources(value: Any) -> dict[str, list[dict]]:
    out = {"data_sources": [], "field_mappings": []}
    for table in _as_items(value):
        name = table.get("name") or table.get("table") or table.get("source")
        if not name:
            continue
        fields = table.get("fields") or table.get("columns") or table.get("schema") or {}
        source = {
            "name": str(name),
            "type": table.get("type", "table"),
            "fields": _fields_dict(fields),
            "owner": table.get("owner"),
            "freshness": table.get("freshness"),
            "sensitivity": table.get("sensitivity"),
            "status": table.get("status", "candidate"),
        }
        out["data_sources"].append(source)
        for field in _field_names(fields):
            out["field_mappings"].append({
                "source": str(name),
                "source_field": field,
                "target": _field_target(field, table),
                "status": table.get("mapping_status", "unknown"),
            })
    return out


def _fields_dict(fields: Any) -> dict:
    if isinstance(fields, dict):
        return fields
    if isinstance(fields, list):
        result = {}
        for field in fields:
            if isinstance(field, dict):
                name = field.get("name") or field.get("field") or field.get("column")
                if name:
                    result[str(name)] = field.get("type", "STRING")
            elif field:
                result[str(field)] = "STRING"
        return result
    if isinstance(fields, str):
        return {name: "STRING" for name in _split_names(fields)}
    return {}


def _field_names(fields: Any) -> list[str]:
    if isinstance(fields, dict):
        return [str(k) for k in fields]
    if isinstance(fields, list):
        names = []
        for field in fields:
            if isinstance(field, dict):
                name = field.get("name") or field.get("field") or field.get("column")
                if name:
                    names.append(str(name))
            elif field:
                names.append(str(field))
        return names
    if isinstance(fields, str):
        return _split_names(fields)
    return []


def _field_target(field: str, table: dict) -> str:
    mappings = table.get("mappings") or table.get("field_mappings") or {}
    if isinstance(mappings, dict) and field in mappings:
        return str(mappings[field])
    return f"TBD.{field}"


def _key_values(text: str) -> dict[str, str]:
    aliases = {
        "actor": "actor", "user": "actor", "stakeholder": "actor",
        "decision maker": "actor", "행위자": "actor", "사용자": "actor",
        "담당자": "actor", "고객": "actor",
        "goal": "goal", "business goal": "goal", "목표": "goal",
        "decision": "decision", "의사결정": "decision", "판단": "decision",
        "success metric": "success_metric", "metric": "success_metric",
        "success_metric": "success_metric", "성공지표": "success_metric", "지표": "success_metric",
        "scope": "scope", "범위": "scope",
        "question": "question", "competency question": "question", "질문": "question",
        "event": "event", "domain event": "event", "이벤트": "event",
        "table": "data_source", "source": "data_source", "data source": "data_source",
        "데이터": "data_source", "테이블": "data_source", "소스": "data_source",
        "entities": "entities", "entity": "entities", "엔티티": "entities",
        "relations": "relations", "relation": "relations", "관계": "relations",
    }
    facts: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"\s*[-*]?\s*([^:=：]{2,40})\s*[:=：]\s*(.+?)\s*$", line)
        if not m:
            continue
        key = re.sub(r"\s+", " ", m.group(1).strip().lower())
        canonical = aliases.get(key)
        if canonical:
            facts[canonical] = m.group(2).strip()
    return facts


def _story_from_facts(facts: dict[str, str]) -> dict[str, Any] | None:
    keys = {"actor", "goal", "decision", "success_metric", "scope"}
    if not any(facts.get(k) for k in keys):
        return None
    return {
        "actor": facts.get("actor", "Stakeholder"),
        "goal": facts.get("goal", ""),
        "decision": facts.get("decision", ""),
        "success_metric": facts.get("success_metric", ""),
        "scope": facts.get("scope", ""),
        "priority": "high",
        "status": "candidate",
    }


def _infer_story(text: str) -> dict[str, Any] | None:
    actor = _infer_actor(text)
    goal = _infer_after(text, [
        r"wants? to ([^.\n;]+)",
        r"needs? to ([^.\n;]+)",
        r"goal is ([^.\n;]+)",
        r"목표는?\s*([^.\n;]+)",
    ])
    decision = _infer_after(text, [
        r"decision (?:is|to improve is|will improve) ([^.\n;]+)",
        r"decide whether ([^.\n;]+)",
        r"identify ([^.\n;]+)",
        r"determine ([^.\n;]+)",
        r"판단(?:은|할 것은)?\s*([^.\n;]+)",
        r"결정(?:은|할 것은)?\s*([^.\n;]+)",
    ])
    metric = _infer_after(text, [
        r"success metric is ([^.\n;]+)",
        r"measure(?:d)? by ([^.\n;]+)",
        r"reduce ([^.\n;]+)",
        r"성공지표는?\s*([^.\n;]+)",
    ])
    if not (actor or goal or decision):
        return None
    return {
        "actor": actor or "Stakeholder",
        "goal": goal or decision or text[:160],
        "decision": decision or goal or text[:160],
        "success_metric": metric or "",
        "priority": "high",
        "status": "candidate",
    }


def _infer_actor(text: str) -> str:
    patterns = [
        r"\b([A-Z][A-Za-z ]{2,45}?(?:manager|owner|analyst|planner|engineer|operator|team|user|customer|stakeholder|admin|lead))\b",
        r"([가-힣A-Za-z0-9 ]{2,30}(?:관리자|담당자|팀|사용자|고객|분석가|운영자|기획자|엔지니어))",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1).strip(" ,.;")
    return ""


def _infer_after(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1).strip(" ,.;")
    return ""


def _questions_from_text(text: str) -> list[str]:
    questions = []
    for line in re.split(r"[\n]+", text):
        line = line.strip(" -\t")
        if not line:
            continue
        if "?" in line:
            for part in line.split("?"):
                part = part.strip()
                if part:
                    questions.append(part + "?")
        elif re.search(r"\b(which|what|who|where|when|how many|how much|why)\b", line, re.I):
            questions.append(line)
        elif re.search(r"(어떤|무엇|누가|언제|어디|얼마나|몇|왜|어떻게)", line):
            questions.append(line)
    return _unique_strings(questions, limit=8)


def _answer_shape(question: str, state: dict[str, Any],
                  context: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for name in context.get("entity_names") or []:
        if str(name).lower() in question.lower():
            candidates.append(str(name))
    for item in _list(state.get("model_candidates")):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if name and str(name).lower() in question.lower():
            candidates.append(str(name))
    for token in re.findall(r"\b[A-Z][A-Za-z0-9_]{2,}\b", question):
        if token not in {"Which", "What", "When", "Where", "How", "Why"}:
            candidates.append(token)
    return _unique_strings(candidates, limit=5)


def _events_from_text(text: str, stage: str) -> list[dict[str, Any]]:
    if stage != "event_discovery" and not _contains_any(text, _EVENT_HINTS):
        return []
    events = []
    for sentence in _sentences(text)[:8]:
        if not _contains_any(sentence, _EVENT_HINTS):
            continue
        events.append({
            "name": _event_name(sentence),
            "text": sentence,
            "trigger": _infer_after(sentence, [
                r"when ([^.\n;]+)",
                r"after ([^.\n;]+)",
                r"trigger(?:ed)? by ([^.\n;]+)",
                r"트리거(?:는|가)?\s*([^.\n;]+)",
            ]),
            "state_change": sentence if re.search(r"state|상태|changed|변경|전이", sentence, re.I) else "",
            "status": "candidate",
        })
    return events


def _data_items_from_text(text: str, facts: dict[str, str],
                          stage: str) -> dict[str, list[dict]]:
    out = {"data_sources": [], "field_mappings": []}
    if facts.get("data_source"):
        out["data_sources"].append({
            "name": _safe_name(facts["data_source"]),
            "type": "table",
            "status": "candidate",
        })
    if not (_contains_any(text, _DATA_HINTS) or stage == "data_grounding"):
        return {}
    for m in re.finditer(r"([A-Za-z][A-Za-z0-9_\-]*)\s*\(([^\)]{3,300})\)", text):
        table = m.group(1)
        fields = _split_names(m.group(2))
        if not fields:
            continue
        out["data_sources"].append({
            "name": table,
            "type": "table",
            "fields": {field: "STRING" for field in fields},
            "status": "candidate",
        })
        for field in fields:
            out["field_mappings"].append({
                "source": table,
                "source_field": field,
                "target": f"TBD.{field}",
                "status": "unknown",
            })
    return {k: v for k, v in out.items() if v}


def _model_items_from_facts(facts: dict[str, str], text: str,
                            stage: str) -> dict[str, list[dict]]:
    out = {"model_candidates": []}
    if facts.get("entities"):
        for name in _split_names(facts["entities"]):
            out["model_candidates"].append({
                "kind": "entity",
                "name": _safe_label(name),
                "status": "candidate",
            })
    if facts.get("relations"):
        for name in _split_names(facts["relations"]):
            out["model_candidates"].append({
                "kind": "relation",
                "name": _safe_label(name).upper(),
                "status": "candidate",
            })
    if stage == "model_synthesis" and not out["model_candidates"]:
        for token in re.findall(r"\b[A-Z][A-Za-z0-9_]{2,}\b", text):
            if token not in {"RDF", "SHACL", "SPARQL", "JSON"}:
                out["model_candidates"].append({
                    "kind": "entity",
                    "name": _safe_label(token),
                    "status": "candidate",
                })
    return {k: v for k, v in out.items() if v}


def _review_items_from_text(text: str, stage: str) -> dict[str, list[dict]]:
    out = {"risks": [], "assumptions": [], "review_findings": [], "action_items": []}
    if stage != "adversarial_review" and not re.search(
        r"risk|assumption|missing|unknown|ambiguous|conflict|위험|가정|누락|모호|충돌|확인",
        text, re.I,
    ):
        return {}
    for sentence in _sentences(text)[:10]:
        lower = sentence.lower()
        if re.search(r"assumption|assume|가정", lower):
            out["assumptions"].append({"text": sentence, "status": "assumed"})
        elif re.search(r"risk|missing|unknown|conflict|위험|누락|불명|충돌", lower):
            out["risks"].append({"text": sentence, "status": "open"})
        elif re.search(r"action|todo|owner|확인|해야|필요", lower):
            out["action_items"].append({
                "text": sentence,
                "owner": "customer",
                "status": "open",
            })
        elif stage == "adversarial_review":
            out["review_findings"].append({"text": sentence, "status": "open"})
    return {k: v for k, v in out.items() if v}


def _rdf_items_from_text(text: str) -> dict[str, list[dict]]:
    if not _contains_any(text, _RDF_HINTS):
        return {}
    items = []
    iri = re.search(r"https?://[^\s,;\)]+", text)
    if iri:
        items.append({
            "topic": "base_iri",
            "value": iri.group(0).rstrip("."),
            "status": "candidate",
        })
    for hint in _RDF_HINTS:
        if hint.lower() in text.lower():
            items.append({
                "topic": hint.upper() if hint in {"rdf", "shacl", "sparql"} else hint,
                "text": text[:300],
                "status": "candidate",
            })
            break
    return {"rdf_decisions": items} if items else {}


def _stage_question(stage: str, missing: str, state: dict[str, Any]) -> str:
    if stage == "inception":
        return (
            "Please give the missing inception evidence: actor, goal, decision, "
            "success metric, and one-day scope. A compact user_story JSON is ideal."
        )
    if stage == "discovery":
        return "Describe one concrete domain scenario from start to finish, including systems and records."
    if stage == "event_discovery":
        return "Name one important business event: what triggers it, what state changes, and what evidence records it?"
    if stage == "story_to_question":
        return "Turn the top user story into one competency question and the expected answer shape."
    if stage == "model_synthesis":
        return "Which candidate entities, relations, event nodes, and properties are needed for the priority question?"
    if stage == "data_grounding":
        return "Provide a source table/file/API schema and map at least one field to a model element."
    if stage == "adversarial_review":
        return "Which assumption, contradiction, missing source, or over-modeled concept should be challenged first?"
    if stage == "validation_handoff":
        return "Which query evidence and owner-tagged action item should be packaged for handoff?"
    return NEXT_QUESTIONS.get(stage, f"Please provide missing evidence: {missing}.")


def _cypher_seed(question: str, answer_shape: Any = None) -> str:
    shape = [_safe_label(x) for x in _list(answer_shape) if _safe_label(x)]
    if len(shape) >= 2:
        nodes = [f"(n{index}:{label})" for index, label in enumerate(shape)]
        pattern = nodes[0] + "".join(
            f"-[r{index}]-{nodes[index + 1]}"
            for index in range(len(nodes) - 1)
        )
        returned = [
            value
            for index in range(len(nodes))
            for value in (
                ([f"n{index}"] if index == 0 else
                 [f"r{index - 1}", f"n{index}"])
            )
        ]
        return f"MATCH {pattern} RETURN {', '.join(returned)} LIMIT 25"
    if len(shape) == 1:
        return f"MATCH (n:{shape[0]}) RETURN n LIMIT 25"
    return "MATCH (n) RETURN n LIMIT 25"


def _sparql_seed(question: str, answer_shape: Any = None) -> str:
    shape = [_safe_label(x) for x in _list(answer_shape) if _safe_label(x)]
    if len(shape) >= 2:
        triples = [f"?n0 a :{shape[0]} ."]
        for index, label in enumerate(shape[1:], start=1):
            triples.append(
                f"?n{index - 1} ?p{index - 1} ?n{index} . "
                f"?n{index} a :{label} .")
        selected = [
            value
            for index in range(len(shape))
            for value in (
                ([f"?n{index}"] if index == 0 else
                 [f"?p{index - 1}", f"?n{index}"])
            )
        ]
        return (
            f"SELECT {' '.join(selected)} WHERE {{ {' '.join(triples)} }} "
            "LIMIT 25"
        )
    if len(shape) == 1:
        return f"SELECT ?s WHERE {{ ?s a :{shape[0]} . }} LIMIT 25"
    return "SELECT * WHERE { ?s ?p ?o . } LIMIT 25"


def _sentences(text: str) -> list[str]:
    return [
        s.strip(" -\t")
        for s in re.split(r"(?<=[.!?。！？])\s+|[\n]+", text)
        if s.strip(" -\t")
    ]


def _split_names(text: Any) -> list[str]:
    if isinstance(text, list):
        return [str(x).strip() for x in text if str(x).strip()]
    return [
        part.strip(" '\"")
        for part in re.split(r"[,;/|]", str(text))
        if part.strip(" '\"")
    ]


def _unique_strings(values: list[str], limit: int = 20) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value.strip())
        if len(result) >= limit:
            break
    return result


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _event_name(sentence: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_]+", sentence)
    if words:
        return "".join(w[:1].upper() + w[1:] for w in words[:3])[:48]
    korean = re.sub(r"[^가-힣A-Za-z0-9]", "", sentence)
    return (korean[:24] or "DomainEvent") + "Event"


def _safe_name(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "_", str(value).strip()) or "source"


def _safe_label(value: Any) -> str:
    raw = str(value).strip()
    raw = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    raw = raw.strip("_") or "Thing"
    if raw[0].isdigit():
        raw = "_" + raw
    return raw


def _norm_value(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).lower()
    return str(value or "").strip().lower()


def _norm_query(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().rstrip(";").lower()
