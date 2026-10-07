# Aggregates

## Agg-Settlement
- **identifying:** settlement_id
- **포함 이벤트:** E-settlement-batch-started, E-settlement-created, E-settlement-failed, E-settlement-confirmed
- **불변식:**
  - 한 settlement는 하나의 merchant에만 속함
  - settlement_date + merchant_id 조합 유일
  - status 전이: pending → completed | failed (failed → pending 재시도 가능)
- **trace_links:** [E-settlement-created, E-settlement-failed, cand-Settlement]

## Agg-Merchant
- **identifying:** merchant_id (UUID) + business_registration_no (자연키)
- **포함 이벤트:** E-merchant-onboarded, E-merchant-updated (Phase 4에서 추가 발견)
- **불변식:**
  - business_registration_no는 영구적 (변경 시 새 가맹점)
  - status 전이: active → suspended → terminated (역방향 가능)
- **trace_links:** [cand-Merchant]

## Agg-Payout
- **identifying:** payout_id
- **포함 이벤트:** E-payout-notified, E-payout-paid
- **불변식:**
  - 한 payout은 하나의 settlement에 속함
  - status: pending → paid | failed
- **trace_links:** [cand-Payout, E-payout-notified, E-payout-paid]

## Agg-PaymentTransaction (BC-Payment 소속)
- **identifying:** payment_transaction_id
- **포함 이벤트:** E-payment-transaction-approved (BC-Payment 내부)
- **메모:** BC-Settlement 관점에서는 외부 이벤트로 유입. 본 워크플로우 깊이=Standard에서는 Settlement 컨텍스트 중심으로 다룸.
