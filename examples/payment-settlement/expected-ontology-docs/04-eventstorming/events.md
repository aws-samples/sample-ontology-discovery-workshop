# Domain Events

## E-payment-transaction-approved
- **라벨:** 결제 거래 승인됨
- **시간:** T-1 (정산 전날 발생)
- **출처:** story-001 step 1 (이벤트 외부, BC-Payment에서 유입)
- **personas:** [P-merchant (간접)]
- **trace_links:** [story-001, cand-PaymentTransaction]

## E-settlement-batch-started
- **라벨:** 정산 배치 시작됨
- **시간:** T+0 (새벽 2시)
- **출처:** story-001 step 1
- **personas:** [P-system-batch]
- **trace_links:** [story-001]

## E-settlement-created
- **라벨:** 정산 생성됨
- **시간:** T+1
- **출처:** story-001 step 3
- **personas:** [P-system-batch]
- **trace_links:** [story-001, cand-Settlement, Act-S1-A3]

## E-payout-notified
- **라벨:** 정산 알림 발송됨
- **시간:** T+2
- **출처:** story-001 step 4
- **personas:** [P-system-batch, P-merchant]
- **trace_links:** [story-001, Act-S1-A4]

## E-settlement-failed
- **라벨:** 정산 실패됨
- **시간:** T+1 (실패 분기)
- **출처:** story-001 exception
- **personas:** [P-system-batch, P-pgops]
- **trace_links:** [story-001 exception, cand-SettlementFailure]
- **메모:** Hotspot H1과 연관

## E-settlement-confirmed
- **라벨:** 정산 확인됨
- **시간:** T+24 (가맹점주가 보고서 확인)
- **출처:** story-001 step 6
- **personas:** [P-merchant]
- **trace_links:** [story-001, Act-S1-A6]

## E-payout-paid
- **라벨:** 지급 완료됨
- **시간:** T+24~T+72 (은행 이체 완료)
- **출처:** story-001 step 4 후속, payouts.status=paid
- **personas:** [P-system-batch (간접)]
- **trace_links:** [cand-Payout]
