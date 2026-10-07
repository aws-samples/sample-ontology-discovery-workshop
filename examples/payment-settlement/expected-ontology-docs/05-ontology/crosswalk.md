# Crosswalk: raw-schemas ↔ ontology

## schemas/ddl.sql

### merchants (DDL table)
| Column | Ontology Mapping | Confidence | Note |
|---|---|---|---|
| id | Ent-Merchant.merchant_id | high | PK |
| business_registration_no | Ent-Merchant.business_registration_no | high | 자연키 |
| name | Ent-Merchant.name | high | |
| contact_email | Ent-Merchant.contact_email | medium | PII, ontology 노출 결정 |
| bank_account | Ent-Merchant.bank_account | medium | PII, ontology에 표기만: 실제 값은 별도 |
| status | Ent-Merchant.status | high | enum |
| onboarded_at | Ent-Merchant.onboarded_at | high | |
| created_at | (system) | low | 도메인 의미 없음 |
| updated_at | (system) | low | 도메인 의미 없음 |

### payment_transactions (DDL table)
| Column | Ontology Mapping | Confidence | Note |
|---|---|---|---|
| id | Ent-PaymentTransaction.payment_transaction_id | high | |
| merchant_id | Rel-Merchant-PaymentTransaction via | high | FK |
| amount | Ent-PaymentTransaction.amount | high | |
| currency | Ent-PaymentTransaction.currency | high | |
| payment_method | Ent-PaymentTransaction.payment_method | high | enum |
| approved_at | Ent-PaymentTransaction.approved_at | high | |
| status | Ent-PaymentTransaction.status | high | enum, refunded는 out-of-scope |
| settlement_id | Rel-Settlement-PaymentTransaction via | high | FK nullable |

### settlements (DDL table)
| Column | Ontology Mapping | Confidence | Note |
|---|---|---|---|
| id | Ent-Settlement.settlement_id | high | PK |
| merchant_id | Rel-Merchant-Settlement via | high | FK |
| settlement_date | Ent-Settlement.settlement_date | high | (merchant_id, date) UNIQUE |
| total_amount | Ent-Settlement.total_amount | high | |
| transaction_count | Ent-Settlement.transaction_count | high | |
| status | Ent-Settlement.status | high | enum |
| settled_at | Ent-Settlement.settled_at | high | |

### payouts (DDL table)
| Column | Ontology Mapping | Confidence | Note |
|---|---|---|---|
| id | Ent-Payout.payout_id | high | |
| settlement_id | Rel-Settlement-Payout via | high | FK |
| amount | Ent-Payout.amount | high | |
| paid_at | Ent-Payout.paid_at | high | |
| status | Ent-Payout.status | high | enum |
| bank_transaction_ref | Ent-Payout.bank_transaction_ref | medium | |

### settlement_failures (DDL table)
| Column | Ontology Mapping | Confidence | Note |
|---|---|---|---|
| id | Ent-SettlementFailure.settlement_failure_id | high | |
| settlement_id | Rel-Settlement-SettlementFailure via | high | FK |
| failed_at | Ent-SettlementFailure.failed_at | high | |
| reason | Ent-SettlementFailure.reason | medium | |
| retry_count | Ent-SettlementFailure.retry_count | high | |
| resolved_at | Ent-SettlementFailure.resolved_at | medium | nullable |

## openapi.yaml

### components.schemas.Settlement
| Field | Ontology Mapping | Note |
|---|---|---|
| payout (단일) | Rel-Settlement-Payout (1:N으로 resolved) | OpenAPI 단순화였음. DDL이 진실. |

### components.schemas.Payout
| Field | Ontology Mapping | Note |
|---|---|---|
| settlementId | Rel-Settlement-Payout via (역방향) | |

## 해결된 충돌

### C1: Settlement-Payout 카디널리티
- **해결:** DDL 1:N 채택. OpenAPI는 별도 PR에서 단일 → 배열로 수정 권고.
- **사용자 결정 시점:** Phase 5 Q3.
- **audit:** 2026-05-26 (예시).
