"""도메인별 워크샵 시연 — mock 추출이 실제로 의미있는 그래프를 만드는지 검증."""
from ontology_workshop.graph import OntologyGraph
from ontology_workshop import skills as sk

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


def run_domain(name: str, utterance: str):
    g = OntologyGraph(f"./_t_{abs(hash(name))}.kuzu", fresh=True)
    print(f"\n=== {name} ===")
    r1 = sk.run_skill("extract_entities", utterance)
    sk.apply_to_graph(g, "extract_entities", r1["result"])
    ents = list(g.entity_types.keys())
    print(f"엔티티({len(ents)}): {', '.join(ents)}")

    ctx = {"entities": ents, "relations": []}
    r2 = sk.run_skill("define_relations", utterance, ctx)
    sk.apply_to_graph(g, "define_relations", r2["result"])
    rels = list(g.relation_types.keys())
    print(f"관계({len(rels)}): {', '.join(rels)}")


if __name__ == "__main__":
    for name, utt in DOMAINS:
        run_domain(name, utt)
    print("\n전부 통과 ✓")
