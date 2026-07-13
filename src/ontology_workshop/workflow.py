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
    "risks",
    "decisions",
    "review_findings",
    "action_items",
    "validation_queries",
    "rdf_decisions",
)

_COLLECTION_PREFIX = {
    "claims": "claim",
    "user_stories": "story",
    "domain_events": "event",
    "competency_questions": "question",
    "model_candidates": "model",
    "data_sources": "source",
    "field_mappings": "mapping",
    "assumptions": "assumption",
    "risks": "risk",
    "decisions": "decision",
    "review_findings": "finding",
    "action_items": "action",
    "validation_queries": "query",
    "rdf_decisions": "rdf",
}

_UNIQUE_KEYS = {
    "claims": ("text",),
    "user_stories": ("actor", "goal", "decision"),
    "domain_events": ("name", "text"),
    "competency_questions": ("question", "text"),
    "model_candidates": ("kind", "name", "source_element"),
    "data_sources": ("name",),
    "field_mappings": ("source", "source_field", "target"),
    "assumptions": ("text",),
    "risks": ("text",),
    "decisions": ("text", "decision"),
    "review_findings": ("text",),
    "action_items": ("text", "target"),
    "validation_queries": ("language", "query", "question_id"),
    "rdf_decisions": ("topic", "value", "text"),
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
            "version": "ai-odlc-v1",
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
            "risks": [],
            "decisions": [],
            "review_findings": [],
            "action_items": [],
            "validation_queries": [],
            "rdf_decisions": [],
            "last_extraction": {},
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
        if not isinstance(base.get("last_extraction"), dict):
            base["last_extraction"] = {}
        self.data = base
        self.touch()

    def touch(self) -> None:
        self.data["updated_at"] = _now()

    def to_dict(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        out = copy.deepcopy(self.data)
        out["stage_label"] = STAGE_LABELS.get(
            out.get("current_stage"), out.get("current_stage", ""))
        gates = self.gates(context)
        out["gates"] = gates
        passed = sum(1 for g in gates.values() if g["status"] == "pass")
        out["progress"] = {
            "passed": passed,
            "total": len(STAGES),
            "percent": round((passed / len(STAGES)) * 100),
        }
        return out

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
        clean = _clean_item(copy.deepcopy(item or {}))
        if not clean.get("id"):
            clean["id"] = self._next_id(collection, prefix)
        clean.setdefault("stage", self.data["current_stage"])
        clean.setdefault("status", "candidate")
        clean.setdefault("source", "user")
        clean.setdefault("created_at", _now())
        clean["updated_at"] = _now()
        self.data[collection].append(clean)
        self.touch()
        return clean

    def add_unique_item(self, collection: str, prefix: str,
                        item: dict[str, Any]) -> dict[str, Any]:
        """Add item unless an equivalent workflow evidence row already exists."""
        clean = _clean_item(copy.deepcopy(item or {}))
        existing = self._find_equivalent(collection, clean)
        if existing:
            changed = False
            for key, value in clean.items():
                if key in {"id", "created_at"} or value in (None, "", [], {}):
                    continue
                if not existing.get(key):
                    existing[key] = value
                    changed = True
            if changed:
                existing["updated_at"] = _now()
                self.touch()
            return existing
        return self.add_item(collection, prefix, clean)

    def _find_equivalent(self, collection: str,
                         item: dict[str, Any]) -> dict[str, Any] | None:
        keys = _UNIQUE_KEYS.get(collection, ("text", "name", "question"))
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
        stage = stage if stage in STAGES else self.data["current_stage"]
        status = status if status in CLAIM_STATUSES else "candidate"
        claim = self.add_item("claims", "claim", {
            "text": text,
            "stage": stage,
            "role": role,
            "status": status,
            "source": source,
        })
        self.data["current_stage"] = stage
        self.data["active_question"] = NEXT_QUESTIONS.get(stage, "")
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
                item.setdefault("stage", active_stage)
                item.setdefault("source", source)
                item.setdefault("claim_id", claim.get("id"))
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
            question.setdefault("cypher_candidate", query)
            question.setdefault("sparql_candidate", _sparql_seed(qtext, answer_shape))
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
        """Return one focused next question based on the first weak gate."""
        gates = self.gates(context)
        stage = self.data.get("current_stage")
        for candidate in STAGES:
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
        self.data["current_stage"] = "inception"
        self.data["active_question"] = NEXT_QUESTIONS["inception"]
        self.touch()
        return self.to_dict()

    def advance(self, stage: str | None = None, force: bool = False,
                context: dict[str, Any] | None = None) -> dict[str, Any]:
        current = self.data["current_stage"]
        target = stage
        if target is None:
            idx = STAGES.index(current)
            target = STAGES[min(idx + 1, len(STAGES) - 1)]
        if target not in STAGES:
            raise ValueError(f"unknown workflow stage {target}")
        gates = self.gates(context)
        current_gate = gates[current]
        if not force and current_gate["status"] != "pass":
            return {
                "ok": False,
                "blocked": True,
                "stage": current,
                "gate": current_gate,
                "workflow": self.to_dict(context),
            }
        self.data["current_stage"] = target
        self.data["active_question"] = NEXT_QUESTIONS[target]
        self.touch()
        return {"ok": True, "stage": target, "workflow": self.to_dict(context)}

    def add_review(self, findings: list[dict] | None = None,
                   assumptions: list[dict] | None = None,
                   risks: list[dict] | None = None,
                   action_items: list[dict] | None = None) -> dict[str, Any]:
        added = {"review_findings": [], "assumptions": [], "risks": [], "action_items": []}
        for item in findings or []:
            added["review_findings"].append(
                self.add_unique_item("review_findings", "finding", item))
        for item in assumptions or []:
            added["assumptions"].append(
                self.add_unique_item("assumptions", "assumption", item))
        for item in risks or []:
            added["risks"].append(self.add_unique_item("risks", "risk", item))
        for item in action_items or []:
            added["action_items"].append(
                self.add_unique_item("action_items", "action", item))
        return added

    def generate_review(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate an evidence-based adversarial review from current gaps."""
        gates = self.gates(context)
        findings: list[dict[str, Any]] = []
        risks: list[dict[str, Any]] = []
        assumptions: list[dict[str, Any]] = []
        action_items: list[dict[str, Any]] = []

        for stage, gate in gates.items():
            if gate.get("status") == "pass":
                continue
            missing = ", ".join(gate.get("missing") or []) or "required evidence"
            findings.append({
                "text": f"{STAGE_LABELS.get(stage, stage)} gate lacks {missing}.",
                "severity": "high" if gate.get("status") == "fail" else "medium",
                "status": "open",
                "stage": stage,
            })
            action_items.append({
                "text": f"Provide or confirm {missing} for {STAGE_LABELS.get(stage, stage)}.",
                "owner": "customer",
                "status": "open",
                "stage": stage,
            })

        for story in _list(self.data.get("user_stories")):
            if isinstance(story, dict) and not _has_text(story, "success_metric"):
                assumptions.append({
                    "text": "A user story exists without an explicit success metric.",
                    "status": "assumed",
                    "owner": story.get("actor", "customer"),
                    "stage": story.get("stage", "inception"),
                })

        for q in _list(self.data.get("competency_questions")):
            if isinstance(q, dict) and not q.get("expected_answer_shape"):
                findings.append({
                    "text": (
                        "Competency question needs an expected answer shape: "
                        f"{q.get('question') or q.get('text')}"
                    ),
                    "severity": "medium",
                    "status": "open",
                    "stage": q.get("stage", "story_to_question"),
                })

        for mapping in _list(self.data.get("field_mappings")):
            if not isinstance(mapping, dict):
                continue
            status = _readiness_status(mapping.get("status") or mapping.get("readiness"))
            if status in {"missing", "unknown"}:
                risks.append({
                    "text": (
                        f"Data mapping for {mapping.get('target', 'model element')} "
                        f"is {status}."
                    ),
                    "severity": "high" if status == "missing" else "medium",
                    "status": "open",
                    "stage": "data_grounding",
                })

        if not self.data.get("rdf_decisions"):
            risks.append({
                "text": "RDF handoff lacks confirmed base IRI/URI generation decisions.",
                "severity": "medium",
                "status": "open",
                "stage": "adversarial_review",
            })

        return self.add_review(findings, assumptions, risks, action_items)

    def record_query_verification(self, question: str | None, cypher: str,
                                  result: dict[str, Any]) -> dict[str, Any]:
        """Attach openCypher execution evidence to matching workflow query seeds."""
        question = (question or "").strip()
        cypher = (cypher or "").strip()
        if not question and not cypher:
            return {"updated": 0}
        ok = bool(result.get("ok"))
        evidence = {
            "verified_at": _now(),
            "ok": ok,
            "count": result.get("count", 0),
            "columns": result.get("columns", []),
            "error": result.get("error"),
        }
        updated = 0
        for item in _list(self.data.get("validation_queries")):
            if not isinstance(item, dict):
                continue
            if str(item.get("language", "")).lower() != "opencypher":
                continue
            if not _query_matches(item, question, cypher):
                continue
            item["status"] = "verified" if ok else "failed"
            item["readiness"] = "verified" if ok else "needs_fix"
            item.setdefault("verification_evidence", [])
            item["verification_evidence"].append(evidence)
            item["updated_at"] = _now()
            updated += 1
        for q in _list(self.data.get("competency_questions")):
            if not isinstance(q, dict):
                continue
            qtext = q.get("question") or q.get("text") or ""
            if question and _norm_value(qtext) == _norm_value(question):
                q["query_readiness"] = "verified" if ok else "needs_fix"
                q["verification_status"] = "verified" if ok else "failed"
                q["last_verification"] = evidence
                q["updated_at"] = _now()
        if updated:
            self.touch()
        return {"updated": updated, "evidence": evidence}

    def gates(self, context: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
        ctx = context or {}
        graph = _dict(ctx.get("graph"))
        verified_count = int(ctx.get("verified_count") or 0)
        gates: dict[str, dict[str, Any]] = {}

        stories = _list(self.data.get("user_stories"))
        decisions = _list(self.data.get("decisions"))
        inception_ok = any(
            _has_text(s, "actor") and _has_text(s, "goal")
            and _has_text(s, "decision") for s in stories
        )
        if not inception_ok:
            inception_ok = bool(decisions and _has_text(decisions[0], "text", "decision"))
        gates["inception"] = _gate(
            inception_ok,
            missing=[] if inception_ok else [
                "actor", "goal", "decision", "success metric or explicit scope"
            ],
            evidence={"user_stories": len(stories), "decisions": len(decisions)},
        )

        discovery_claims = [
            c for c in _list(self.data.get("claims"))
            if c.get("stage") in {"discovery", "inception"} and _has_text(c, "text")
        ]
        gates["discovery"] = _gate(
            len(discovery_claims) > 0,
            missing=[] if discovery_claims else ["domain narrative claim"],
            evidence={"claims": len(discovery_claims)},
        )

        events = _list(self.data.get("domain_events"))
        gates["event_discovery"] = _gate(
            len(events) > 0,
            missing=[] if events else ["domain events or explicit no-event rationale"],
            evidence={"domain_events": len(events)},
        )

        questions = _list(self.data.get("competency_questions"))
        gates["story_to_question"] = _gate(
            len(stories) > 0 and len(questions) > 0,
            missing=[
                *([] if stories else ["user story"]),
                *([] if questions else ["competency question"]),
            ],
            evidence={"user_stories": len(stories), "competency_questions": len(questions)},
        )

        candidates = _list(self.data.get("model_candidates"))
        graph_has_model = (
            int(graph.get("entities") or 0) > 0 and int(graph.get("relations") or 0) > 0
        )
        gates["model_synthesis"] = _gate(
            bool(candidates) or graph_has_model,
            missing=[] if (candidates or graph_has_model)
            else ["model candidates or graph T-Box"],
            evidence={
                "model_candidates": len(candidates),
                "entities": graph.get("entities", 0),
                "relations": graph.get("relations", 0),
            },
        )

        sources = _list(self.data.get("data_sources"))
        mappings = _list(self.data.get("field_mappings"))
        readiness = {
            _readiness_status(m.get("status") or m.get("readiness"))
            for m in mappings if isinstance(m, dict)
        }
        gates["data_grounding"] = _gate(
            len(sources) > 0 and len(mappings) > 0,
            missing=[
                *([] if sources else ["data source"]),
                *([] if mappings else ["field mapping"]),
            ],
            evidence={
                "data_sources": len(sources),
                "field_mappings": len(mappings),
                "readiness": sorted(readiness),
            },
        )

        review_count = (
            len(_list(self.data.get("review_findings")))
            + len(_list(self.data.get("assumptions")))
            + len(_list(self.data.get("risks")))
        )
        gates["adversarial_review"] = _gate(
            review_count > 0,
            missing=[] if review_count else ["review findings, assumptions, or risks"],
            evidence={
                "review_findings": len(_list(self.data.get("review_findings"))),
                "assumptions": len(_list(self.data.get("assumptions"))),
                "risks": len(_list(self.data.get("risks"))),
            },
        )

        action_items = _list(self.data.get("action_items"))
        gates["validation_handoff"] = _gate(
            verified_count > 0 and len(action_items) > 0,
            missing=[
                *([] if verified_count else ["verified query"]),
                *([] if action_items else ["handoff action item"]),
            ],
            evidence={"verified_queries": verified_count, "action_items": len(action_items)},
        )
        return gates


def _gate(ok: bool, missing: list[str],
          evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    status = "pass" if ok else ("partial" if evidence and any(evidence.values()) else "fail")
    return {"status": status, "missing": missing, "evidence": evidence or {}}


def _query_matches(item: dict[str, Any], question: str, cypher: str) -> bool:
    if question and _norm_value(item.get("question")) == _norm_value(question):
        return True
    if cypher and _norm_value(item.get("query")) == _norm_value(cypher):
        return True
    return False


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
        return f"MATCH (a:{shape[0]})-[r]-(b:{shape[1]}) RETURN a, r, b LIMIT 25"
    if len(shape) == 1:
        return f"MATCH (n:{shape[0]}) RETURN n LIMIT 25"
    return "MATCH (n) RETURN n LIMIT 25"


def _sparql_seed(question: str, answer_shape: Any = None) -> str:
    shape = [_safe_label(x) for x in _list(answer_shape) if _safe_label(x)]
    if len(shape) >= 2:
        return (
            f"SELECT ?a ?p ?b WHERE {{ ?a a :{shape[0]} ; ?p ?b . "
            f"?b a :{shape[1]} . }} LIMIT 25"
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
