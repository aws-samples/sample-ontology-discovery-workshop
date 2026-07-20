"""도메인별 워크샵 시연 — mock 추출이 실제로 의미있는 그래프를 만드는지 검증."""
from ontology_workshop.graph import OntologyGraph
from ontology_workshop import skills as sk
from ontology_workshop.workflow import STAGES, WorkflowState

DOMAINS = [
    ("미디어/엔터테인먼트",
     "우리는 OTT 서비스라 시청자가 콘텐츠를 시청하고, 시리즈와 에피소드가 있어요. "
     "채널과 제작사, 출연진 정보도 있고 광고와 추천이 핵심입니다."),
    ("게임",
     "플레이어가 게임을 플레이하고 캐릭터와 아이템을 보유합니다. 길드에 가입하고 "
     "매치와 토너먼트에 참여하며 업적을 달성합니다."),
    ("스포츠",
     "선수가 팀에 소속되어 리그에서 경기를 합니다. 감독이 팀을 지휘하고, "
     "선수마다 스탯과 부상 기록, 트레이닝 이력이 있습니다."),
    ("제조/하이테크",
     "제품은 부품으로 구성되고 부품은 자재로 만들어집니다. 공장의 생산라인에서 "
     "공정을 거치고 작업자가 설비를 운용해요. 공급업체에서 자재가 오고 품질 검사로 "
     "불량을 잡습니다. 센서가 설비에 붙어서 알람을 생성해요."),
    ("텔코",
     "가입자가 요금제에 가입하고 회선과 단말기를 사용합니다. 통화 기록과 청구서가 "
     "있고 기지국 정보, 약정 그리고 해지 이력을 관리합니다."),
    ("자동차",
     "차량은 차종과 트림이 있고 딜러를 통해 고객에게 판매됩니다. 정비 이력과 "
     "리콜 영향이 차량별로 관리됩니다."),
    ("복합기업(엔터프라이즈)",
     "지주회사 아래 계열사가 있고 각 계열사에는 사업부와 부서가 있습니다. "
     "직원이 부서에 소속되고 프로젝트를 수행합니다."),
]

REQUIRED_ARTIFACTS = {
    key: f"./exports/domain-neutral/{key}"
    for key in (
        "report_markdown", "report_html", "snapshot_html", "snapshot_json",
        "neptune_cypher", "neptune_nodes", "neptune_edges", "rdf_ontology",
        "rdf_instances", "rdf_jsonld", "rdf_shacl", "rdf_sparql",
        "rdf_mapping", "rdf_neptune_handoff", "workshop_zip",
    )
}


def workflow_context(g, workflow):
    tbox = g.tbox()
    snapshot = g.snapshot()
    context = {
        "graph": {
            "entities": len(tbox["entities"]),
            "relations": len(tbox["relations"]),
            "nodes": len(snapshot["nodes"]),
            "edges": len(snapshot["edges"]),
        },
        "entity_names": list(tbox["entities"]),
        "relation_names": list(tbox["relations"]),
        "tbox": tbox,
        "rdf_validation_source_fingerprint": "domain-rdf-source",
        "handoff_manifest_files_valid": True,
    }
    context["query_source_fingerprint"] = workflow.query_source_fingerprint(
        tbox, snapshot)
    context["handoff_source_fingerprint"] = workflow.handoff_source_fingerprint(
        context["rdf_validation_source_fingerprint"])
    return context


def verify_domain_neutral_gates(name, g):
    """Prove the same gate predicates work without domain-name branches."""
    workflow = WorkflowState()
    entity_names = list(g.entity_types)
    relation_items = list(g.relation_types.values())
    if not relation_items:
        raise AssertionError(f"{name}: no relation is available for a competency pattern")
    first, second = relation_items[0].src, relation_items[0].dst
    story = workflow.add_item("user_stories", "story", {
        "actor": f"{name} decision owner",
        "goal": f"Understand the relationship between {first} and {second}",
        "decision": "Choose the next domain action",
        "success_metric": "Answer the priority question during the workshop",
        "scope": "One representative scenario in the one-day workshop",
        "priority": "high",
    })
    claim = workflow.add_item("claims", "claim", {
        "text": f"A representative {name} scenario connects {first} and {second}.",
        "stage": "discovery", "story_ids": [story["id"]],
        "definitions": {first: f"A working {name} term"},
    })
    workflow.decide_item(
        "claims", claim["id"], "confirm",
        note="The domain owner confirmed the narrative and working term.")
    workflow.add_item("domain_events", "event", {
        "name": "PriorityStateChanged",
        "trigger": "A domain decision is recorded",
        "state_change": "The tracked item moves to its next business state",
        "modeling_decision": "event_node",
    })
    question = workflow.add_item("competency_questions", "question", {
        "question": f"Which {first} instances are connected to {second} instances?",
        "expected_answer_shape": [first, second],
        "story_ids": [story["id"]], "priority": "high",
    })
    for entity in entity_names:
        et = g.entity_types[entity]
        workflow.add_item("model_candidates", "model", {
            "kind": "entity", "name": entity,
            "properties": et.properties, "primary_key": et.primary_key,
            "question_ids": [question["id"]],
        })
    for relation in relation_items:
        workflow.add_item("model_candidates", "model", {
            "kind": "relation", "name": relation.name,
            "src": relation.src, "dst": relation.dst,
            "properties": relation.properties,
            "question_ids": [question["id"]],
        })
    source = workflow.add_item("data_sources", "source", {
        "name": "representative_source", "type": "table",
        "owner": "domain-data-owner", "freshness": "workshop sample",
    })
    for index, target in enumerate((first, second), start=1):
        workflow.add_item("field_mappings", "mapping", {
            "source": source["name"], "source_field": f"field_{index}",
            "target": target, "status": "available",
        })
    workflow.add_item("action_items", "action", {
        "text": "Confirm production extraction ownership after the workshop.",
        "owner": "domain-data-owner", "status": "open",
    })

    context = workflow_context(g, workflow)
    workflow._refresh_query_candidates(context)
    context = workflow_context(g, workflow)
    query = next(
        item for item in workflow.data["validation_queries"]
        if item.get("question_id") == question["id"]
        and str(item.get("language")).lower() == "opencypher")
    verification = workflow.record_query_verification(
        question["question"], query["query"],
        {"ok": True, "count": 1, "columns": ["a", "r", "b"]}, context)
    if verification.get("qualified") != 1:
        raise AssertionError(f"{name}: priority query did not qualify")
    context = workflow_context(g, workflow)
    review = workflow.generate_review(context)
    for collection in ("review_findings", "contradictions", "risks"):
        for item in review[collection]:
            if item.get("source") == "automatic_adversarial_review":
                workflow.decide_item(
                    collection, item["id"], "resolve",
                    note="The domain owner reviewed this bounded workshop finding.")
    for stage in STAGES[1:]:
        advanced = workflow.advance(stage=stage, context=workflow_context(g, workflow))
        if not advanced.get("ok"):
            raise AssertionError(
                f"{name}: could not advance sequentially to {stage}: {advanced}")
    context = workflow_context(g, workflow)
    workflow.record_handoff_manifest({
        "source_fingerprint": context["handoff_source_fingerprint"],
        "artifacts": REQUIRED_ARTIFACTS,
    })
    context = workflow_context(g, workflow)
    gates = workflow.gates(context)
    failures = {
        stage: gate["missing"] for stage, gate in gates.items()
        if gate["status"] != "pass"
    }
    if failures:
        raise AssertionError(f"{name}: domain-neutral workflow gates failed: {failures}")
    if set(gates) != set(STAGES):
        raise AssertionError(f"{name}: workflow stage coverage changed")


def run_domain(name: str, utterance: str):
    g = OntologyGraph(f"./_t_{abs(hash(name))}.kuzu", fresh=True)
    print(f"\n=== {name} ===")
    r1 = sk.run_skill("extract_entities", utterance)
    sk.apply_to_graph(g, "extract_entities", r1["result"])
    ents = list(g.entity_types.keys())
    print(f"엔티티({len(ents)}): {', '.join(ents)}")
    if len(ents) < 2:
        raise AssertionError(f"{name}: expected at least two domain entity types")

    ctx = {"entities": ents, "relations": []}
    r2 = sk.run_skill("define_relations", utterance, ctx)
    sk.apply_to_graph(g, "define_relations", r2["result"])
    rels = list(g.relation_types.keys())
    print(f"관계({len(rels)}): {', '.join(rels)}")
    if not rels:
        raise AssertionError(f"{name}: expected at least one domain relation type")
    for relation in g.relation_types.values():
        if relation.src not in g.entity_types or relation.dst not in g.entity_types:
            raise AssertionError(
                f"{name}: {relation.name} has unknown endpoint "
                f"{relation.src}->{relation.dst}")
    verify_domain_neutral_gates(name, g)
    return {"entities": ents, "relations": rels}


if __name__ == "__main__":
    results = []
    for name, utt in DOMAINS:
        results.append(run_domain(name, utt))
    if len(results) != len(DOMAINS):
        raise AssertionError("not every configured domain scenario was exercised")
    print("\n전부 통과 ✓")
