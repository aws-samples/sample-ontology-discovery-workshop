# Candidate Inventory (자동 추출)

> 주의: 모든 항목은 **candidate**입니다. Phase 5 사용자 검증 후 확정.

## Entities

### [candidate] Merchant
- **자료원:** schemas/ddl.sql:5 (table merchants), openapi.yaml#/components/schemas/Merchant
- **confidence:** high (DDL PK + OpenAPI required + 자연키 명시)
- **속성:**
  - id (UUID, PK): high
  - business_registration_no (VARCHAR UNIQUE, 자연키): high
  - name (VARCHAR): high
  - contact_email (VARCHAR): medium
  - bank_account (VARCHAR): medium (PII 가능성)
  - status (VARCHAR enum): high
  - onboarded_at (TIMESTAMPTZ): high
- **관계 후보:**
  - 1:N → Settlement via merchant_id
  - 1:N → PaymentTransaction via merchant_id
- **사용자 결정 필요:** 도메인 용어 "가맹점" vs "Merchant"

### [candidate] PaymentTransaction
- **자료원:** schemas/ddl.sql:18 (table payment_transactions)
- **confidence:** high
- **속성:**
  - id (UUID, PK): high
  - merchant_id (FK→merchants): high
  - amount (DECIMAL): high
  - currency (CHAR(3)): high
  - payment_method (VARCHAR enum): high
  - approved_at: high
  - status: high
  - settlement_id (FK→settlements, nullable): high
- **사용자 결정 필요:** "결제 거래" 용어 적절성, 환불 status는 out-of-scope

### [candidate] Settlement
- **자료원:** schemas/ddl.sql:35 (table settlements), openapi.yaml#/components/schemas/Settlement
- **confidence:** high (DDL PK + OpenAPI required)
- **속성:**
  - id (UUID, PK): high
  - merchant_id (FK): high
  - settlement_date (DATE): high
  - total_amount (DECIMAL): high
  - transaction_count (INT): high
  - status (enum: pending|completed|failed): high
  - settled_at: high
- **관계 후보:**
  - 1:N → Payout via settlement_id (DDL)
  - 1:1 → Payout (OpenAPI Settlement.payout 단일 필드) 주의: conflicts.md C1
- **사용자 결정 필요:** "정산" 도메인 용어, payout 카디널리티

### [candidate] Payout
- **자료원:** schemas/ddl.sql:53 (table payouts), openapi.yaml#/components/schemas/Payout
- **confidence:** high
- **속성:**
  - id (UUID, PK): high
  - settlement_id (FK): high
  - amount (DECIMAL): high
  - paid_at: high
  - status (enum: pending|paid|failed): high
  - bank_transaction_ref: medium

### [candidate] SettlementFailure
- **자료원:** schemas/ddl.sql:64 (table settlement_failures)
- **confidence:** medium (도메인 의미보다 운영 추적용일 가능성)
- **사용자 결정 필요:** 별도 entity로 둘지, Settlement 안에 fold할지

## Relationships

- [candidate] Merchant 1:N PaymentTransaction (FK merchant_id, high)
- [candidate] Merchant 1:N Settlement (FK merchant_id, high)
- [candidate] Settlement 1:N Payout (DDL, high): OpenAPI는 1:1 (conflicts.md C1)
- [candidate] Settlement 1:N SettlementFailure (FK settlement_id, medium)
- [candidate] PaymentTransaction N:1 Settlement (FK settlement_id nullable, high)

## 사용자 결정이 필요한 항목

1. **용어 매핑**: Merchant/가맹점, Settlement/정산, Payout/지급/입금, PaymentTransaction/결제 거래
2. **Settlement-Payout 카디널리티**: DDL 1:N vs OpenAPI 1:1 (conflicts.md C1)
3. **SettlementFailure**: 별도 entity vs Settlement 내부 상태
4. **PII 처리**: Merchant.contact_email, bank_account를 ontology에 노출할지
5. **out-of-scope 항목**: payment_transactions.status에 'refunded' 있음 → Phase 1 out-of-scope와 충돌
