"""교육 도메인 워크샵 시연 시더.
실제 워크샵에서는 에이전트 스킬이 이 호출들을 대화 결과로부터 생성한다."""
from ontology_workshop.graph import OntologyGraph, EntityType, RelationType
from ontology_workshop.docgen import render_markdown, render_query_evidence


def seed(g: OntologyGraph):
    # --- T-Box: 엔티티 ---
    g.add_entity_type(EntityType("Student", {"name": "STRING", "grade": "INT64"}))
    g.add_entity_type(EntityType("Parent", {"name": "STRING"}))
    g.add_entity_type(EntityType("Teacher", {"name": "STRING", "subject": "STRING"}))
    g.add_entity_type(EntityType("Curriculum", {"title": "STRING", "unit": "INT64"},
                                 primary_key="title"))
    # 이벤트성 엔티티 (모의고사)
    g.add_entity_type(EntityType("MockExam", {"name": "STRING", "date": "STRING"}))

    # --- T-Box: 관계 ---
    g.add_relation_type(RelationType("COMPLETED", "Student", "Curriculum",
                                     "N:M", {"score": "INT64"}))
    g.add_relation_type(RelationType("CHILD_OF", "Student", "Parent", "N:1"))
    g.add_relation_type(RelationType("TEACHES", "Teacher", "Curriculum", "N:M"))
    g.add_relation_type(RelationType("FEEDBACK", "Teacher", "Student",
                                     "N:M", {"note": "STRING"}))
    g.add_relation_type(RelationType("TOOK", "Student", "MockExam",
                                     "N:M", {"score": "INT64"}))

    # --- A-Box: 인스턴스 ---
    g.add_instance("Student", {"name": "김민수", "grade": 2})
    g.add_instance("Parent", {"name": "김영희"})
    g.add_instance("Teacher", {"name": "박선생", "subject": "수학"})
    g.add_instance("Curriculum", {"title": "이차방정식", "unit": 3})
    g.add_instance("Curriculum", {"title": "함수", "unit": 4})
    g.add_instance("MockExam", {"name": "6월 모의고사", "date": "2026-06-04"})

    g.add_edge("COMPLETED", "김민수", "이차방정식", {"score": 92})
    g.add_edge("COMPLETED", "김민수", "함수", {"score": 68})
    g.add_edge("CHILD_OF", "김민수", "김영희")
    g.add_edge("TEACHES", "박선생", "이차방정식")
    g.add_edge("TEACHES", "박선생", "함수")
    g.add_edge("FEEDBACK", "박선생", "김민수", {"note": "함수 단원 보강 필요"})
    g.add_edge("TOOK", "김민수", "6월 모의고사", {"score": 74})


if __name__ == "__main__":
    g = OntologyGraph("./workshop.kuzu", fresh=True)
    seed(g)
    print("=== 시드 완료 ===")
    print(render_markdown(g, "교육 도메인 온톨로지"))
    print("\n=== 질의 검증 (설득 증거) ===")
    q = ("MATCH (s:Student)-[c:COMPLETED]->(cur:Curriculum) "
         "WHERE c.score < 70 "
         "MATCH (t:Teacher)-[f:FEEDBACK]->(s) "
         "RETURN s.name, cur.title, c.score, f.note")
    res = g.query(q)
    print(render_query_evidence(
        "성적이 낮은 단원과 그 학생에 대한 교사 피드백은?", q, res))
