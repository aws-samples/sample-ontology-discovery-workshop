# Ontology: Payment Settlement Domain

## Entities

### Ent-Merchant
- **라벨:** 가맹점 (Merchant)
- **식별자:** merchant_id (UUID, 합성키), business_registration_no (사업자등록번호, 자연키)
- **핵심 속성:**
  - business_registration_no: high
  - name: high
  - status (active|suspended|terminated): high
  - onboarded_at: high
  - bank_account: medium (PII)
- **bounded_context:** BC-Merchant (cross-context: BC-Settlement에서도 참조)
- **trace_links:** [cand-Merchant, P-merchant, story-001, Agg-Merchant]

### Ent-Settlement
- **라벨:** 정산 (Settlement)
- **식별자:** settlement_id (UUID, 합성키)
  - 자연키 후보: (merchant_id, settlement_date): DDL UNIQUE 제약
- **핵심 속성:**
  - merchant_id (FK→Ent-Merchant): high
  - settlement_date: high
  - total_amount: high
  - transaction_count: high
  - status (pending|completed|failed): high
  - settled_at: high
- **bounded_context:** BC-Settlement
- **trace_links:** [cand-Settlement, Agg-Settlement, story-001, E-settlement-created]

### Ent-Payout
- **라벨:** 지급 (Payout)
- **식별자:** payout_id
- **핵심 속성:**
  - settlement_id (FK→Ent-Settlement): high
  - amount: high
  - status (pending|paid|failed): high
  - paid_at: high
  - bank_transaction_ref: medium
- **bounded_context:** BC-Settlement
- **trace_links:** [cand-Payout, Agg-Payout, E-payout-notified, E-payout-paid]

### Ent-PaymentTransaction
- **라벨:** 결제 거래 (Payment Transaction)
- **식별자:** payment_transaction_id
- **핵심 속성:**
  - merchant_id (FK→Ent-Merchant): high
  - amount: high
  - currency: high
  - payment_method: high
  - approved_at: high
  - status (approved|failed|refunded): high (refunded는 out-of-scope)
  - settlement_id (FK→Ent-Settlement, nullable): high
- **bounded_context:** BC-Payment (외부)
- **trace_links:** [cand-PaymentTransaction, story-001 step1]

### Ent-SettlementFailure
- **라벨:** 정산 실패 (Settlement Failure)
- **식별자:** settlement_failure_id
- **핵심 속성:**
  - settlement_id (FK→Ent-Settlement): high
  - failed_at: high
  - reason: medium
  - retry_count: high
  - resolved_at: medium
- **bounded_context:** BC-Settlement
- **trace_links:** [cand-SettlementFailure, E-settlement-failed, hotspot-H1]
- **사용자 결정:** Settlement Aggregate 내부 상태 vs 별도 entity → 별도 entity로 결정 (재시도 이력 추적 가치 + 사용자 운영팀의 명시적 요청)

## Relationships

### Rel-Merchant-Settlement
- **type:** related-to
- **source:** Ent-Settlement
- **target:** Ent-Merchant
- **via:** merchant_id (FK)
- **cardinality:** N:1
- **business meaning:** 정산은 한 가맹점에 귀속
- **trace_links:** [DDL settlements.merchant_id, story-001]

### Rel-Settlement-Payout
- **type:** has-a
- **source:** Ent-Settlement
- **target:** Ent-Payout
- **cardinality:** 1:N
- **resolved_conflict:** DDL이 진실, OpenAPI Settlement.payout 단일 필드는 단순화 (사용자 결정)
- **trace_links:** [conflicts.md C1, Q3]

### Rel-Settlement-PaymentTransaction
- **type:** has-a
- **source:** Ent-Settlement
- **target:** Ent-PaymentTransaction
- **cardinality:** 1:N
- **business meaning:** 한 정산은 여러 결제 거래를 포함(합산)
- **trace_links:** [DDL payment_transactions.settlement_id, story-001 step2]

### Rel-Merchant-PaymentTransaction
- **type:** related-to
- **source:** Ent-PaymentTransaction
- **target:** Ent-Merchant
- **cardinality:** N:1
- **trace_links:** [DDL payment_transactions.merchant_id]

### Rel-Settlement-SettlementFailure
- **type:** has-a
- **source:** Ent-Settlement
- **target:** Ent-SettlementFailure
- **cardinality:** 1:N
- **trace_links:** [DDL settlement_failures.settlement_id]

## Concepts

### Con-Settlement-Cycle
- **라벨:** 정산 주기
- **정의:** 한 가맹점의 결제 거래 → 정산 생성 → 지급 한 사이클 (보통 T-1 결제 → T 정산 → T+1~T+3 지급)
- **포함 entities:** Ent-PaymentTransaction, Ent-Settlement, Ent-Payout
- **trace_links:** [story-001]

### Con-Bounded-Context-Boundary
- **라벨:** 컨텍스트 경계
- **정의:** BC-Payment(결제 발생)와 BC-Settlement(정산 처리)는 동일한 PaymentTransaction을 다른 의미로 본다.
  - BC-Payment에서 PaymentTransaction의 status는 결제 자체의 성공, 실패
  - BC-Settlement에서는 정산 대상 여부(settlement_id의 nullable 여부)
- **trace_links:** [bounded-contexts.md]

## Bounded Contexts

- **BC-Merchant**: Ent-Merchant (master data)
- **BC-Payment**: Ent-PaymentTransaction (결제 발생, 외부)
- **BC-Settlement**: Ent-Settlement, Ent-Payout, Ent-SettlementFailure (이번 워크플로우 핵심)
