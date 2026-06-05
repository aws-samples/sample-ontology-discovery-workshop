# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""M1 — 워크샵 스킬 엔진.

대화(고객 답변 텍스트) → 구조화 JSON → 검증 → 그래프 반영 루프를 자동화한다.
각 스킬은 두 가지 추출 경로를 가진다:
  1) Claude API (ANTHROPIC_API_KEY 있을 때) — Sonnet에 JSON-only 프롬프트
  2) 오프라인 mock 추출기 — 키가 없을 때 규칙 기반(현장 데모 안정성)

스킬 출력은 graph.OntologyGraph에 그대로 반영 가능한 형태로 정규화된다.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .graph import OntologyGraph, EntityType, RelationType
from .security import (
    audit_log,
    sanitize_llm_input,
    validate_https_url,
    validate_identifier,
    validate_property_schema,
)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("ONTOFORGE_MODEL", "claude-sonnet-4-20250514")


# ---------------------------------------------------------------------------
# 스킬 정의: 이름, 시스템 프롬프트, mock 추출기
# ---------------------------------------------------------------------------
@dataclass
class Skill:
    name: str
    system: str
    mock: Callable[[str, dict], dict]


def _json_only(instruction: str) -> str:
    return (
        instruction
        + "\n\n반드시 유효한 JSON 객체 하나만 출력한다. "
        "서문, 설명, 마크다운 코드펜스 없이 JSON만 반환한다."
    )


# ---- 1. extract_entities --------------------------------------------------
ENTITY_SYS = _json_only(
    "너는 온톨로지 모델러다. 고객이 도메인을 한국어/영어로 설명한 텍스트에서 "
    "엔티티 타입(개념)과 인스턴스(구체 사례)를 분리해 추출한다. "
    "엔티티 타입명은 반드시 영문 PascalCase로 표준화한다 "
    "(예: 학생→Student, 가입자→Subscriber, 콘텐츠→Content, 부품→Component, "
    "차량→Vehicle, 공정→Process, 계열사→Subsidiary). "
    "도메인 표준 용어가 있으면 그것을 따른다. "
    "스키마: {\"entity_types\":[{\"name\":\"PascalCase\",\"properties\":{\"prop\":\"STRING|INT64|DOUBLE|BOOLEAN\"},\"primary_key\":\"name\"}],"
    "\"instances\":[{\"etype\":\"...\",\"props\":{...}}]}"
)

# 한국어/영어 흔한 도메인 명사 → 엔티티 타입 힌트(mock용).
# API 추출이 안 될 때를 위한 오프라인 폴백. 도메인별로 정리되어 있다.
_ENTITY_HINTS = {
    # --- 교육 ---
    "학생": ("Student", {"name": "STRING", "grade": "INT64"}, "name"),
    "학부모": ("Parent", {"name": "STRING"}, "name"),
    "부모": ("Parent", {"name": "STRING"}, "name"),
    "선생": ("Teacher", {"name": "STRING", "subject": "STRING"}, "name"),
    "교사": ("Teacher", {"name": "STRING", "subject": "STRING"}, "name"),
    "커리큘럼": ("Curriculum", {"title": "STRING", "unit": "INT64"}, "title"),
    "단원": ("Curriculum", {"title": "STRING", "unit": "INT64"}, "title"),
    "모의고사": ("MockExam", {"name": "STRING", "date": "STRING"}, "name"),
    "시험": ("Exam", {"name": "STRING", "date": "STRING"}, "name"),
    "수업": ("Lesson", {"title": "STRING"}, "title"),

    # --- 미디어/엔터테인먼트 ---
    "콘텐츠": ("Content", {"title": "STRING", "runtime": "INT64"}, "title"),
    "영상": ("Content", {"title": "STRING", "runtime": "INT64"}, "title"),
    "시리즈": ("Series", {"title": "STRING", "season": "INT64"}, "title"),
    "에피소드": ("Episode", {"title": "STRING", "number": "INT64"}, "title"),
    "시청자": ("Viewer", {"id": "STRING", "name": "STRING"}, "id"),
    "채널": ("Channel", {"name": "STRING"}, "name"),
    "광고": ("Ad", {"id": "STRING", "title": "STRING"}, "id"),
    "제작사": ("Studio", {"name": "STRING"}, "name"),
    "배우": ("CastMember", {"name": "STRING", "role": "STRING"}, "name"),
    "출연진": ("CastMember", {"name": "STRING", "role": "STRING"}, "name"),
    "추천": ("Recommendation", {"id": "STRING"}, "id"),

    # --- 게임 ---
    "플레이어": ("Player", {"id": "STRING", "nickname": "STRING"}, "id"),
    "게임": ("Game", {"title": "STRING", "genre": "STRING"}, "title"),
    "캐릭터": ("Character", {"id": "STRING", "name": "STRING", "class": "STRING"}, "id"),
    "아이템": ("Item", {"id": "STRING", "name": "STRING", "rarity": "STRING"}, "id"),
    "길드": ("Guild", {"name": "STRING"}, "name"),
    "클랜": ("Guild", {"name": "STRING"}, "name"),
    "매치": ("GameMatch", {"id": "STRING", "date": "STRING"}, "id"),
    "토너먼트": ("Tournament", {"name": "STRING", "date": "STRING"}, "name"),
    "업적": ("Achievement", {"id": "STRING", "name": "STRING"}, "id"),

    # --- 스포츠 ---
    "선수": ("Athlete", {"name": "STRING", "position": "STRING"}, "name"),
    "팀": ("Team", {"name": "STRING", "league": "STRING"}, "name"),
    "경기": ("SportsMatch", {"id": "STRING", "date": "STRING"}, "id"),
    "리그": ("League", {"name": "STRING", "season": "STRING"}, "name"),
    "시즌": ("Season", {"year": "INT64", "league": "STRING"}, "year"),
    "코치": ("Coach", {"name": "STRING"}, "name"),
    "감독": ("Coach", {"name": "STRING"}, "name"),
    "경기장": ("Venue", {"name": "STRING", "capacity": "INT64"}, "name"),
    "스타디움": ("Venue", {"name": "STRING", "capacity": "INT64"}, "name"),
    "스탯": ("Stat", {"id": "STRING", "metric": "STRING"}, "id"),
    "부상": ("Injury", {"id": "STRING", "type": "STRING", "date": "STRING"}, "id"),
    "트레이닝": ("Training", {"id": "STRING", "date": "STRING"}, "id"),

    # --- 제조/하이테크 ---
    "제품": ("Product", {"sku": "STRING", "name": "STRING"}, "sku"),
    "부품": ("Component", {"part_no": "STRING", "name": "STRING"}, "part_no"),
    "컴포넌트": ("Component", {"part_no": "STRING", "name": "STRING"}, "part_no"),
    "자재": ("Material", {"id": "STRING", "name": "STRING"}, "id"),
    "원자재": ("Material", {"id": "STRING", "name": "STRING"}, "id"),
    "공장": ("Factory", {"name": "STRING", "location": "STRING"}, "name"),
    "생산라인": ("ProductionLine", {"id": "STRING", "factory": "STRING"}, "id"),
    "공정": ("Process", {"id": "STRING", "name": "STRING"}, "id"),
    "설비": ("Equipment", {"id": "STRING", "name": "STRING"}, "id"),
    "장비": ("Equipment", {"id": "STRING", "name": "STRING"}, "id"),
    "작업자": ("Operator", {"id": "STRING", "name": "STRING"}, "id"),
    "공급업체": ("Supplier", {"name": "STRING"}, "name"),
    "협력사": ("Supplier", {"name": "STRING"}, "name"),
    "주문": ("Order", {"id": "STRING", "date": "STRING"}, "id"),
    "검사": ("Inspection", {"id": "STRING", "date": "STRING"}, "id"),
    "품질": ("QualityCheck", {"id": "STRING", "result": "STRING"}, "id"),
    "결함": ("Defect", {"id": "STRING", "type": "STRING"}, "id"),
    "불량": ("Defect", {"id": "STRING", "type": "STRING"}, "id"),
    "로트": ("Lot", {"id": "STRING", "date": "STRING"}, "id"),
    "배치": ("Lot", {"id": "STRING", "date": "STRING"}, "id"),
    "센서": ("Sensor", {"id": "STRING", "type": "STRING"}, "id"),
    "알람": ("Alert", {"id": "STRING", "severity": "STRING"}, "id"),
    "알림": ("Alert", {"id": "STRING", "severity": "STRING"}, "id"),
    "이상치": ("Anomaly", {"id": "STRING", "type": "STRING"}, "id"),

    # --- 텔코 ---
    "가입자": ("Subscriber", {"id": "STRING", "name": "STRING"}, "id"),
    "회선": ("Line", {"msisdn": "STRING"}, "msisdn"),
    "요금제": ("Plan", {"name": "STRING", "price": "INT64"}, "name"),
    "통화": ("Call", {"id": "STRING", "date": "STRING", "duration": "INT64"}, "id"),
    "청구서": ("Bill", {"id": "STRING", "amount": "INT64"}, "id"),
    "기지국": ("BaseStation", {"id": "STRING", "location": "STRING"}, "id"),
    "단말기": ("Device", {"imei": "STRING", "model": "STRING"}, "imei"),
    "약정": ("Contract", {"id": "STRING", "term_months": "INT64"}, "id"),
    "해지": ("Churn", {"id": "STRING", "date": "STRING"}, "id"),
    "이탈": ("Churn", {"id": "STRING", "date": "STRING"}, "id"),

    # --- 자동차 ---
    "차량": ("Vehicle", {"vin": "STRING", "model": "STRING"}, "vin"),
    "차종": ("VehicleModel", {"name": "STRING", "year": "INT64"}, "name"),
    "트림": ("Trim", {"name": "STRING", "model": "STRING"}, "name"),
    "딜러": ("Dealer", {"name": "STRING", "region": "STRING"}, "name"),
    "리콜": ("Recall", {"id": "STRING", "reason": "STRING"}, "id"),
    "정비": ("ServiceRecord", {"id": "STRING", "date": "STRING"}, "id"),

    # --- 공통 (엔터프라이즈/복합기업) ---
    "고객": ("Customer", {"id": "STRING", "name": "STRING"}, "id"),
    "직원": ("Employee", {"id": "STRING", "name": "STRING"}, "id"),
    "사용자": ("AppUser", {"id": "STRING", "name": "STRING"}, "id"),
    "회사": ("Organization", {"name": "STRING"}, "name"),
    "조직": ("Organization", {"name": "STRING"}, "name"),
    "계열사": ("Subsidiary", {"name": "STRING", "parent": "STRING"}, "name"),
    "사업부": ("BusinessUnit", {"name": "STRING"}, "name"),
    "부서": ("Department", {"name": "STRING"}, "name"),
    "프로젝트": ("Project", {"id": "STRING", "name": "STRING"}, "id"),
    "결제": ("Payment", {"id": "STRING", "amount": "INT64"}, "id"),
    "구매": ("Purchase", {"id": "STRING", "date": "STRING"}, "id"),
}


def _mock_entities(text: str, ctx: dict) -> dict:
    found: dict[str, tuple] = {}
    for kw, spec in _ENTITY_HINTS.items():
        if kw in text:
            found[spec[0]] = spec
    entity_types = [
        {"name": n, "properties": p, "primary_key": pk}
        for (n, p, pk) in found.values()
    ]
    return {"entity_types": entity_types, "instances": []}


# ---- 2. define_relations --------------------------------------------------
RELATION_SYS = _json_only(
    "너는 온톨로지 모델러다. 주어진 엔티티 타입 목록과 고객 설명에서 "
    "엔티티 간 관계(엣지)와 카디널리티를 추출한다. "
    "관계 이름은 반드시 영문 UPPER_SNAKE_CASE 동사형으로 표준화한다 "
    "(예: 완료→COMPLETED, 시청→VIEWED, 구성→COMPOSED_OF, 가입→SUBSCRIBES_TO, "
    "보유→OWNS, 리콜영향→AFFECTED_BY). "
    "스키마: {\"relations\":[{\"name\":\"UPPER_SNAKE\",\"src\":\"Entity\",\"dst\":\"Entity\","
    "\"cardinality\":\"1:N|N:1|N:M\",\"properties\":{\"prop\":\"TYPE\"}}],"
    "\"edges\":[{\"rtype\":\"...\",\"src_key\":\"...\",\"dst_key\":\"...\",\"props\":{...}}]}"
)


def _mock_relations(text: str, ctx: dict) -> dict:
    ents = set(ctx.get("entities", []))
    rels = []
    # 자동 발견: src·dst 엔티티가 둘 다 있으면 관계 추가
    template = [
        # 교육
        ("COMPLETED", "Student", "Curriculum", "N:M", {"score": "INT64"}),
        ("CHILD_OF", "Student", "Parent", "N:1", {}),
        ("TEACHES", "Teacher", "Curriculum", "N:M", {}),
        ("FEEDBACK", "Teacher", "Student", "N:M", {"note": "STRING"}),
        ("TOOK", "Student", "MockExam", "N:M", {"score": "INT64"}),
        # 미디어
        ("VIEWED", "Viewer", "Content", "N:M", {"timestamp": "STRING", "duration": "INT64"}),
        ("APPEARS_IN", "CastMember", "Content", "N:M", {"role": "STRING"}),
        ("PRODUCED_BY", "Content", "Studio", "N:1", {}),
        ("PART_OF", "Episode", "Series", "N:1", {}),
        ("AIRED_ON", "Content", "Channel", "N:M", {"date": "STRING"}),
        ("RECOMMENDED_TO", "Recommendation", "Viewer", "N:1", {}),
        ("RECOMMENDS", "Recommendation", "Content", "N:1", {}),
        # 게임
        ("PLAYS", "Player", "Game", "N:M", {"hours": "INT64"}),
        ("OWNS_CHARACTER", "Player", "Character", "1:N", {}),
        ("HAS_ITEM", "Character", "Item", "N:M", {"quantity": "INT64"}),
        ("MEMBER_OF", "Player", "Guild", "N:1", {}),
        ("PARTICIPATED", "Player", "GameMatch", "N:M", {"result": "STRING"}),
        ("UNLOCKED", "Player", "Achievement", "N:M", {"date": "STRING"}),
        ("PURCHASED", "Player", "Item", "N:M", {"price": "INT64"}),
        # 스포츠
        ("PLAYS_FOR", "Athlete", "Team", "N:1", {"jersey": "INT64"}),
        ("COACHES", "Coach", "Team", "N:1", {}),
        ("PLAYED_IN", "Athlete", "SportsMatch", "N:M", {"minutes": "INT64"}),
        ("HOSTED_AT", "SportsMatch", "Venue", "N:1", {}),
        ("BELONGS_TO_LEAGUE", "Team", "League", "N:1", {}),
        ("HAS_STAT", "Athlete", "Stat", "1:N", {"value": "DOUBLE"}),
        ("HAS_INJURY", "Athlete", "Injury", "1:N", {}),
        ("ATTENDED", "Athlete", "Training", "N:M", {}),
        # 제조 (BOM·공정·품질·IoT)
        ("COMPOSED_OF", "Product", "Component", "N:M", {"quantity": "INT64"}),
        ("MADE_OF", "Component", "Material", "N:M", {}),
        ("PRODUCED_AT", "Product", "Factory", "N:1", {}),
        ("RUNS_ON", "ProductionLine", "Factory", "N:1", {}),
        ("STEP_OF", "Process", "ProductionLine", "N:1", {}),
        ("OPERATES", "Operator", "Equipment", "N:M", {}),
        ("SUPPLIED_BY", "Material", "Supplier", "N:1", {}),
        ("INSPECTED_BY", "Product", "QualityCheck", "1:N", {}),
        ("HAS_DEFECT", "Product", "Defect", "1:N", {}),
        ("BELONGS_TO_LOT", "Product", "Lot", "N:1", {}),
        ("INSTALLED_ON", "Sensor", "Equipment", "N:1", {}),
        ("TRIGGERED", "Sensor", "Alert", "1:N", {}),
        ("DETECTED", "Sensor", "Anomaly", "1:N", {}),
        # 텔코
        ("SUBSCRIBES_TO", "Subscriber", "Plan", "N:1", {"since": "STRING"}),
        ("HAS_LINE", "Subscriber", "Line", "1:N", {}),
        ("USES_DEVICE", "Subscriber", "Device", "N:M", {}),
        ("MADE_CALL", "Line", "Call", "1:N", {}),
        ("BILLED", "Subscriber", "Bill", "1:N", {}),
        ("COVERED_BY", "Call", "BaseStation", "N:1", {}),
        ("BOUND_BY", "Subscriber", "Contract", "1:N", {}),
        ("CHURNED", "Subscriber", "Churn", "1:1", {}),
        # 자동차
        ("IS_MODEL", "Vehicle", "VehicleModel", "N:1", {}),
        ("HAS_TRIM", "Vehicle", "Trim", "N:1", {}),
        ("SOLD_BY", "Vehicle", "Dealer", "N:1", {"date": "STRING"}),
        ("OWNED_BY", "Vehicle", "Customer", "N:M", {"since": "STRING"}),
        ("SERVICED_AT", "Vehicle", "ServiceRecord", "1:N", {}),
        ("AFFECTED_BY", "Vehicle", "Recall", "N:M", {}),
        # 엔터프라이즈/복합기업
        ("WORKS_AT", "Employee", "Organization", "N:1", {}),
        ("PART_OF_ORG", "Subsidiary", "Organization", "N:1", {}),
        ("HAS_BU", "Subsidiary", "BusinessUnit", "1:N", {}),
        ("BELONGS_TO_DEPT", "Employee", "Department", "N:1", {}),
        ("LEADS", "Employee", "Project", "1:N", {}),
        ("PARTICIPATES", "Employee", "Project", "N:M", {}),
        ("PAID", "Customer", "Payment", "1:N", {}),
        ("PURCHASED_BY", "Purchase", "Customer", "N:1", {}),
    ]
    for name, s, d, card, props in template:
        if s in ents and d in ents:
            rels.append({"name": name, "src": s, "dst": d,
                         "cardinality": card, "properties": props})
    return {"relations": rels, "edges": []}


# ---- 3. model_properties --------------------------------------------------
PROPERTY_SYS = _json_only(
    "너는 온톨로지 모델러다. 점수·완료여부 같은 속성과 모의고사 같은 "
    "이벤트성 엔티티를 도출한다. 출력은 extract_entities와 동일한 스키마"
    "(entity_types + instances)를 따른다."
)


def _mock_properties(text: str, ctx: dict) -> dict:
    return _mock_entities(text, ctx)


# ---- 4. analyze_gaps ------------------------------------------------------
GAP_SYS = _json_only(
    "너는 온톨로지 검토자다. 고객의 질문 리스트와 현재 T-Box(엔티티/관계)를 보고, "
    "질문을 그래프 쿼리로 풀려면 빠진 엔티티/관계가 무엇인지 도출한다. "
    "스키마: {\"missing_entities\":[\"...\"],\"missing_relations\":[{\"name\":\"...\",\"src\":\"...\",\"dst\":\"...\"}],\"rationale\":\"...\"}"
)


def _mock_gaps(text: str, ctx: dict) -> dict:
    ents = set(ctx.get("entities", []))
    rels = set(ctx.get("relations", []))
    missing_e, missing_r, why = [], [], []
    t = text
    # 교육
    if ("재학습" in t or "보강" in t) and "REQUESTED_RELEARN" not in rels:
        missing_r.append({"name": "REQUESTED_RELEARN", "src": "Teacher", "dst": "Curriculum"})
        why.append("‘재학습/보강 요청’ 질문을 풀려면 교사→단원 보강요청 관계가 필요")
    if ("출결" in t or "출석" in t) and "Attendance" not in ents:
        missing_e.append("Attendance")
        why.append("‘출결’ 질문을 풀려면 출결 엔티티가 필요")
    if ("알람" in t or "알림" in t) and "NOTIFY" not in rels:
        missing_r.append({"name": "NOTIFY", "src": "Teacher", "dst": "Parent"})
        why.append("‘알림’ 질문을 풀려면 교사→학부모 알림 관계가 필요")
    # 미디어
    if "추천" in t and "Recommendation" not in ents:
        missing_e.append("Recommendation")
        why.append("‘추천’ 질문을 풀려면 추천 엔티티가 필요")
    # 텔코
    if ("이탈" in t or "해지" in t) and "Churn" not in ents:
        missing_e.append("Churn")
        why.append("‘이탈/해지’ 질문을 풀려면 Churn 엔티티가 필요")
    # 자동차
    if "리콜" in t and "Recall" not in ents:
        missing_e.append("Recall")
        why.append("‘리콜’ 질문을 풀려면 Recall 엔티티가 필요")
    # 제조
    if ("이상치" in t or "이상 탐지" in t or "이상탐지" in t) and "Anomaly" not in ents:
        missing_e.append("Anomaly")
        why.append("‘이상 탐지’ 질문을 풀려면 Anomaly 엔티티가 필요")
    if "BOM" in t.upper() and "COMPOSED_OF" not in rels:
        missing_r.append({"name": "COMPOSED_OF", "src": "Product", "dst": "Component"})
        why.append("‘BOM’ 질문을 풀려면 제품→부품 구성 관계가 필요")
    return {"missing_entities": missing_e, "missing_relations": missing_r,
            "rationale": " / ".join(why) or "현재 T-Box로 충분해 보임"}


# ---- 5. verify_query ------------------------------------------------------
QUERY_SYS = _json_only(
    "너는 openCypher 전문가다. 자연어 질문을 주어진 T-Box(엔티티/관계 스키마)에 맞는 "
    "openCypher 쿼리로 변환한다. Kùzu/Neptune 호환 문법만 사용한다. "
    "스키마: {\"question\":\"...\",\"cypher\":\"MATCH ... RETURN ...\"}"
)


def _mock_query(text: str, ctx: dict) -> dict:
    t = text
    if ("낮" in t or "부족" in t or "보강" in t) and "피드백" in t:
        cy = ("MATCH (s:Student)-[c:COMPLETED]->(cur:Curriculum) WHERE c.score < 70 "
              "MATCH (te:Teacher)-[f:FEEDBACK]->(s) "
              "RETURN s.name, cur.title, c.score, f.note")
    elif "모의고사" in t:
        cy = ("MATCH (s:Student)-[e:TOOK]->(m:MockExam) "
              "RETURN s.name, m.name, e.score ORDER BY e.score")
    elif "완료" in t or "이수" in t:
        cy = ("MATCH (s:Student)-[c:COMPLETED]->(cur:Curriculum) "
              "RETURN s.name, cur.title, c.score")
    # 미디어
    elif "시청" in t or "본 콘텐츠" in t:
        cy = ("MATCH (v:Viewer)-[r:VIEWED]->(c:Content) "
              "RETURN v.name, c.title, r.duration ORDER BY r.duration DESC")
    elif "추천" in t:
        cy = ("MATCH (r:Recommendation)-[:RECOMMENDS]->(c:Content), "
              "(r)-[:RECOMMENDED_TO]->(v:Viewer) RETURN v.name, c.title")
    # 게임
    elif "길드" in t or "클랜" in t:
        cy = ("MATCH (p:Player)-[:MEMBER_OF]->(g:Guild) "
              "RETURN g.name, count(p) AS members ORDER BY members DESC")
    # 스포츠
    elif "선수" in t and ("통계" in t or "기록" in t or "스탯" in t):
        cy = ("MATCH (a:Athlete)-[h:HAS_STAT]->(s:Stat) "
              "RETURN a.name, s.metric, h.value ORDER BY h.value DESC")
    # 제조
    elif "BOM" in t.upper() or "부품 구성" in t or "구성품" in t:
        cy = ("MATCH (p:Product)-[c:COMPOSED_OF]->(comp:Component) "
              "RETURN p.sku, comp.part_no, c.quantity")
    elif "불량" in t or "결함" in t:
        cy = ("MATCH (p:Product)-[:HAS_DEFECT]->(d:Defect) "
              "RETURN p.sku, d.type, count(*) AS cnt ORDER BY cnt DESC")
    elif "이상" in t and ("센서" in t or "탐지" in t):
        cy = ("MATCH (s:Sensor)-[:DETECTED]->(a:Anomaly) "
              "RETURN s.id, a.type, count(*) AS cnt")
    # 텔코
    elif "통화" in t or "사용량" in t:
        cy = ("MATCH (sub:Subscriber)-[:HAS_LINE]->(l:Line)-[:MADE_CALL]->(c:Call) "
              "RETURN sub.name, sum(c.duration) AS total_sec ORDER BY total_sec DESC")
    elif "이탈" in t or "해지" in t:
        cy = ("MATCH (sub:Subscriber)-[:CHURNED]->(c:Churn) "
              "RETURN sub.id, c.date ORDER BY c.date DESC")
    # 자동차
    elif "리콜" in t:
        cy = ("MATCH (v:Vehicle)-[:AFFECTED_BY]->(r:Recall) "
              "RETURN r.reason, count(v) AS vehicles ORDER BY vehicles DESC")
    else:
        cy = "MATCH (n) RETURN n LIMIT 25"
    return {"question": text, "cypher": cy}


# ---- 6. map_data_sources --------------------------------------------------
SOURCE_SYS = _json_only(
    "너는 데이터 아키텍트다. 확정된 T-Box를 보고 어떤 데이터가 이미 있을 법한지"
    "(보유)와 새로 마련해야 하는지(미보유)를 분류하고 스키마 힌트를 단다. "
    "스키마: {\"available\":[{\"entity\":\"...\",\"source\":\"...\",\"schema\":\"...\"}],"
    "\"to_be_sourced\":[{\"entity\":\"...\",\"note\":\"...\"}]}"
)


def _mock_sources(text: str, ctx: dict) -> dict:
    ents = ctx.get("entities", [])
    # 운영 DB에 통상 존재할 만한 엔티티들
    common = {
        # 교육
        "Student", "Teacher", "Parent", "Curriculum", "Lesson",
        # 미디어
        "Content", "Viewer", "Channel", "Series", "Episode",
        # 게임
        "Player", "Game", "Match",
        # 스포츠
        "Athlete", "Team", "League", "SportsMatch",
        # 제조
        "Product", "Component", "Material", "Factory", "ProductionLine",
        "Supplier", "Equipment", "Operator",
        # 텔코
        "Subscriber", "Line", "Plan", "Bill", "Device",
        # 자동차
        "Vehicle", "VehicleModel", "Dealer",
        # 엔터프라이즈
        "Customer", "Employee", "Organization", "Department",
    }
    avail, tbs = [], []
    for e in ents:
        if e in common:
            avail.append({"entity": e, "source": "운영/마스터 DB",
                          "schema": f"{e.lower()}(id, name, ...)"})
        else:
            tbs.append({"entity": e, "note": "별도 수집/정의 필요"})
    return {"available": avail, "to_be_sourced": tbs}


SKILLS: dict[str, Skill] = {
    "extract_entities": Skill("extract_entities", ENTITY_SYS, _mock_entities),
    "define_relations": Skill("define_relations", RELATION_SYS, _mock_relations),
    "model_properties": Skill("model_properties", PROPERTY_SYS, _mock_properties),
    "analyze_gaps": Skill("analyze_gaps", GAP_SYS, _mock_gaps),
    "verify_query": Skill("verify_query", QUERY_SYS, _mock_query),
    "map_data_sources": Skill("map_data_sources", SOURCE_SYS, _mock_sources),
}


# ---------------------------------------------------------------------------
# 추출: Claude API 우선, 실패/무키 시 mock
# ---------------------------------------------------------------------------
def _call_claude(system: str, user: str) -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("no api key")
    validate_https_url(ANTHROPIC_URL)
    user = sanitize_llm_input(user)
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 1500,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(ANTHROPIC_URL, data=body, headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    # nosec B310 - URL is validated above and fixed to https://api.anthropic.com.
    with urllib.request.urlopen(req, timeout=60) as r:  # nosec B310
        data = json.loads(r.read())
    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")
    return _parse_json(text)


def _parse_json(text: str) -> dict:
    text = text.strip()
    # 코드펜스 제거
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    # 첫 { ... 마지막 } 추출(여분 텍스트 방어)
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


def run_skill(skill_name: str, user_text: str, ctx: dict | None = None) -> dict:
    """스킬 실행. {ok, source('api'|'mock'), result, error?}"""
    ctx = ctx or {}
    skill = SKILLS.get(skill_name)
    if not skill:
        return {"ok": False, "error": f"unknown skill {skill_name}"}
    payload = sanitize_llm_input(user_text)
    if ctx:
        payload += f"\n\n[현재 컨텍스트]\n{json.dumps(ctx, ensure_ascii=False)}"
    try:
        result = _validate_skill_result(skill_name, _call_claude(skill.system, payload))
        audit_log("skill_executed", skill=skill_name, source="api")
        return {"ok": True, "source": "api", "result": result}
    except Exception as e:  # noqa: BLE001 - fall back to mock
        result = _validate_skill_result(skill_name, skill.mock(user_text, ctx))
        audit_log("skill_executed", skill=skill_name, source="mock")
        return {"ok": True, "source": "mock", "result": result,
                "note": f"API 미사용({e}), 오프라인 추출기로 대체"}


def _validate_skill_result(skill_name: str, result: dict) -> dict:
    """Validate LLM/mock JSON before it reaches Cypher construction."""
    if not isinstance(result, dict):
        raise ValueError(f"{skill_name} returned non-object JSON")

    for et in result.get("entity_types", []):
        et["name"] = validate_identifier(et["name"], "entity type")
        et["primary_key"] = validate_identifier(et.get("primary_key", "name"), "primary key")
        et["properties"] = validate_property_schema(et.get("properties", {}))

    for rt in result.get("relations", []):
        rt["name"] = validate_identifier(rt["name"], "relation type")
        rt["src"] = validate_identifier(rt["src"], "source entity type")
        rt["dst"] = validate_identifier(rt["dst"], "destination entity type")
        rt["properties"] = validate_property_schema(rt.get("properties", {}))

    for inst in result.get("instances", []):
        inst["etype"] = validate_identifier(inst["etype"], "entity type")
        if not isinstance(inst.get("props"), dict):
            raise ValueError("instance props must be an object")
        inst["props"] = {
            validate_identifier(k, "instance property name"): v
            for k, v in inst["props"].items()
        }

    for edge in result.get("edges", []):
        edge["rtype"] = validate_identifier(edge["rtype"], "relation type")
        if not isinstance(edge.get("props", {}), dict):
            raise ValueError("edge props must be an object")
        edge["props"] = {
            validate_identifier(k, "edge property name"): v
            for k, v in edge.get("props", {}).items()
        }

    for name in result.get("missing_entities", []):
        validate_identifier(name, "missing entity type")
    for rt in result.get("missing_relations", []):
        rt["name"] = validate_identifier(rt["name"], "missing relation type")
        rt["src"] = validate_identifier(rt["src"], "missing relation source")
        rt["dst"] = validate_identifier(rt["dst"], "missing relation destination")

    return result


# ---------------------------------------------------------------------------
# 반영: 스킬 결과를 OntologyGraph에 적용
# ---------------------------------------------------------------------------
def apply_to_graph(g: OntologyGraph, skill_name: str, result: dict) -> dict:
    applied = {"entities": 0, "relations": 0, "instances": 0, "edges": 0,
               "errors": []}

    for et in result.get("entity_types", []):
        r = g.add_entity_type(EntityType(
            et["name"], et.get("properties", {}),
            et.get("primary_key", "name")))
        if r.get("ok"):
            applied["entities"] += 1
        else:
            applied["errors"].append(r.get("error"))

    for rt in result.get("relations", []):
        r = g.add_relation_type(RelationType(
            rt["name"], rt["src"], rt["dst"],
            rt.get("cardinality", "N:M"), rt.get("properties", {})))
        if r.get("ok"):
            applied["relations"] += 1
        else:
            applied["errors"].append(r.get("error"))

    for inst in result.get("instances", []):
        r = g.add_instance(inst["etype"], inst["props"])
        if r.get("ok"):
            applied["instances"] += 1
        else:
            applied["errors"].append(r.get("error"))

    for edge in result.get("edges", []):
        r = g.add_edge(edge["rtype"], edge["src_key"],
                       edge["dst_key"], edge.get("props", {}))
        if r.get("ok"):
            applied["edges"] += 1
        else:
            applied["errors"].append(r.get("error"))

    return applied
