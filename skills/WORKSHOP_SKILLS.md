# 워크샵 스킬 명세 (대화 → 구조화 → 그래프 반영)

대화 레이어(Claude)는 고객 답변을 받아 아래 스킬을 단계적으로 실행하고,
각 스킬의 JSON 출력을 OntoForge 서버 REST 엔드포인트로 반영한다.
모든 스킬은 **JSON만** 반환한다(서문/마크다운 금지).

## 1. extract_entities
프롬프트 지침: 고객 답변에서 도메인 개념(엔티티 타입)과 그 인스턴스 후보를 분리.
```json
{
  "entity_types": [
    {"name": "Student", "properties": {"name":"STRING","grade":"INT64"}, "primary_key":"name"}
  ],
  "instances": [
    {"etype": "Student", "props": {"name": "김민수", "grade": 2}}
  ]
}
```
→ `POST /entity` (각 타입), `POST /instance` (각 인스턴스)

## 2. define_relations
```json
{
  "relations": [
    {"name":"COMPLETED","src":"Student","dst":"Curriculum","cardinality":"N:M","properties":{"score":"INT64"}}
  ],
  "edges": [
    {"rtype":"COMPLETED","src_key":"김민수","dst_key":"함수","props":{"score":68}}
  ]
}
```
→ `POST /relation`, `POST /edge`

## 3. model_properties
속성/이벤트성 엔티티(모의고사 등) 도출. 출력 형식은 1·2와 동일(엔티티+관계 혼합).

## 4. analyze_gaps
입력: 고객 질문 리스트 + 현재 T-Box(`GET /snapshot`).
```json
{
  "missing_entities": ["Attendance"],
  "missing_relations": [{"name":"REQUESTED_RELEARN","src":"Teacher","dst":"Curriculum"}],
  "rationale": "‘재학습 요청’ 질문을 풀려면 보강 요청 관계가 필요"
}
```
→ 운영자 확인 후 1·2 스킬로 반영

## 5. verify_query
입력: 자연어 질문. 출력: openCypher.
```json
{"question":"성적 낮은 단원과 교사 피드백?","cypher":"MATCH (s:Student)-[c:COMPLETED]->(cur:Curriculum) WHERE c.score<70 MATCH (t:Teacher)-[f:FEEDBACK]->(s) RETURN s.name,cur.title,c.score,f.note"}
```
→ `POST /query` (question 포함 시 evidence_md 반환)

## 6. map_data_sources
입력: 확정된 T-Box. 출력: 보유/미보유 데이터 명세.
```json
{
  "available": [{"entity":"Student","source":"학사 DB","schema":"students(id,name,grade)"}],
  "to_be_sourced": [{"entity":"MockExam","note":"모의고사 결과는 별도 수집 필요"}]
}
```
→ 인계서(Markdown)에 포함

## 진화 루프
대화 중 T-Box가 바뀌면(예: 모의고사 추가) 1~2 스킬을 다시 돌려 그래프·문서·시각화가 함께 갱신된다. 매 변경은 `/export/neptune`로 언제든 승격 가능.
