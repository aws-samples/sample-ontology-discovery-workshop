# Discovery Intent

## Domain
결제 정산 (B2B Payment Settlement)

## Purpose (1차 사용)
- LLM RAG: 정산 도메인 챗봇, 문서 어시스턴트
- 그래프 DB 적재: Neo4j 등에 적재해 정산 흐름 추적

## Depth
**Standard**: 페르소나, 이벤트, 애그리거트까지

## Personas (seed)
- 가맹점주 (P-seed-1)
- PG 운영팀 (P-seed-2)
- 자동 정산 배치 (P-seed-3)

상세 페르소나 카드는 Phase 3에서 작성됩니다.

## Scope

### In-scope
B2B 정산 일일 배치 흐름. 결제 발생부터 가맹점 입금까지.

### Out-of-scope
- 환불, 분쟁
- B2C 결제 (개인 카드 결제 종단)
- 로열티, 프로모션 정산

## Timeline
B (1개월): Standard 깊이 적합

## Decisions Reasoning
- 깊이=Standard: 1개월 시한 + B2B PoC 목적과 일치
- Out-of-scope의 "환불"은 결제 라이프사이클의 일부지만 별도 워크플로우로 분리하기로 사용자 결정
