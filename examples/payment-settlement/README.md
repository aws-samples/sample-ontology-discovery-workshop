# Example: Payment Settlement Domain

가짜 결제 정산 도메인 샘플. 워크플로우 회귀 검증용.

## 구조

```
payment-settlement/
├── README.md (이 파일)
├── schemas/
│   └── ddl.sql                        # 가짜 DB 스키마
├── openapi.yaml                       # 가짜 API 스펙
└── expected-ontology-docs/             # 워크플로우가 만들어야 할 산출물 예시
    ├── 01-intent/
    │   ├── intent-questions.md
    │   ├── discovery-intent.md
    │   └── personas-seed.md
    ├── 02-data-survey/
    │   └── candidate-inventory.md
    ├── 03-storytelling/
    │   ├── personas.md
    │   └── stories/
    │       └── story-001-daily-settlement.md
    ├── 04-eventstorming/
    │   ├── events.md
    │   └── aggregates.md
    └── 05-ontology/
        ├── ontology.md
        └── crosswalk.md
```

## 사용법 (회귀 검증)

1. 별도 워크스페이스에 이 디렉토리를 복사:
   ```bash
   cp -R payment-settlement /tmp/test-workspace
   cd /tmp/test-workspace
   ```

2. 워크플로우 설치:
   ```bash
   bash <ontology-discovery-workflow>/scripts/install.sh \
     --target=all --workspace=/tmp/test-workspace --no-libs
   ```

3. Claude Code에서 `/onto-discover` 실행. Phase 1에서 다음과 같이 답변:
   - Q1: 결제 정산
   - Q2: A, B (LLM RAG, 그래프 DB)
   - Q3: B (Standard)
   - Q4: 가맹점주, PG 운영팀, 자동 정산 배치
   - Q5: B2B 정산 일일 배치
   - Q6: 환불, B2C 결제, 로열티
   - Q7: B (1개월)

4. Phase 2에서 `schemas/ddl.sql`과 `openapi.yaml`이 자동 스캔되는지 확인.

5. Phase 5 완료 후 산출물을 `expected-ontology-docs/`와 비교(완전 일치는 LLM 비결정성으로 어려움. 핵심 entity, 관계, 페르소나 일치 여부만 검증).

## 도메인 요약

가맹점주가 결제 단말에서 결제를 발생시키면 PG가 매일 새벽 2시에 정산 배치를 돌립니다. 정산 결과는 `settlements` 테이블에 저장되고 가맹점주에게 이메일로 알립니다. 가맹점주는 다음날 오전에 정산 보고서를 확인합니다.

핵심 페르소나: 가맹점주(P-merchant), PG 운영팀(P-pgops), 자동 정산 배치(P-system-batch).
핵심 엔티티: Merchant, Settlement, Payout, PaymentTransaction.
핵심 이벤트: 정산 생성됨, 정산 알림 발송됨, 가맹점 등록됨.
핵심 애그리거트: Settlement, Merchant, Payout.
바운디드 컨텍스트: BC-Settlement, BC-Payment, BC-Merchant.
