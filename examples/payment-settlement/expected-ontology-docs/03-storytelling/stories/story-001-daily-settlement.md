# Story 001: Daily Settlement Batch

- **ID:** story-001
- **트리거:** 매일 새벽 2시 (cron 스케줄)
- **종료 조건:** 모든 가맹점에 정산 결과 알림 완료
- **주 페르소나:** P-system-batch, P-pgops
- **부 페르소나:** P-merchant (관찰자)

## Sequence

| # | Actor | Activity | Work Object |
|---|---|---|---|
| 1 | P-system-batch | 결제 거래 조회한다 | 결제 거래 내역 |
| 2 | P-system-batch | 가맹점별로 합산한다 | 합산 결과 |
| 3 | P-system-batch | 정산 레코드 생성한다 | settlement |
| 4 | P-system-batch | 가맹점주에게 알림 발송한다 | 정산 알림 이메일 |
| 5 | P-pgops | 실패 케이스 검토한다 | 실패 정산 목록 |
| 6 | P-merchant | 정산 보고서 확인한다 | 정산 보고서 |

## Exception Path
- 결제 거래 데이터 누락 시 → P-pgops 수동 보정 (Phase 4 hotspot)
- 가맹점 계좌 정보 오류 시 → 정산 status=failed, retry_count++

## Trace Links
- candidate-inventory: cand-Settlement, cand-Merchant, cand-Payout, cand-PaymentTransaction
- personas: P-merchant, P-pgops, P-system-batch
