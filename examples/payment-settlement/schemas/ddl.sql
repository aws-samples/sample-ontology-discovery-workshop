-- Example DDL for ontology-discovery-workflow regression testing.
-- Domain: B2B payment settlement.

-- ============================================================
-- merchants — 가맹점
-- ============================================================
CREATE TABLE merchants (
    id UUID PRIMARY KEY,
    business_registration_no VARCHAR(20) UNIQUE NOT NULL,  -- 사업자등록번호 (자연키)
    name VARCHAR(200) NOT NULL,
    contact_email VARCHAR(255),
    bank_account VARCHAR(100),
    onboarded_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',          -- active | suspended | terminated
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- payment_transactions — 결제 거래 (BC-Payment)
-- ============================================================
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY,
    merchant_id UUID NOT NULL REFERENCES merchants(id),
    amount DECIMAL(15, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'KRW',
    payment_method VARCHAR(20) NOT NULL,                    -- card | bank | mobile
    approved_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,                            -- approved | failed | refunded
    settlement_id UUID,                                     -- FK→settlements (정산되면 채워짐)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payment_tx_merchant_approved
    ON payment_transactions (merchant_id, approved_at);

-- ============================================================
-- settlements — 정산 (BC-Settlement)
-- ============================================================
CREATE TABLE settlements (
    id UUID PRIMARY KEY,
    merchant_id UUID NOT NULL REFERENCES merchants(id),
    settlement_date DATE NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL,
    transaction_count INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,                            -- pending | completed | failed
    settled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (merchant_id, settlement_date)
);

ALTER TABLE payment_transactions
    ADD CONSTRAINT fk_payment_tx_settlement
    FOREIGN KEY (settlement_id) REFERENCES settlements(id);

-- ============================================================
-- payouts — 지급 (정산 → 가맹점 입금)
-- ============================================================
CREATE TABLE payouts (
    id UUID PRIMARY KEY,
    settlement_id UUID NOT NULL REFERENCES settlements(id),
    amount DECIMAL(15, 2) NOT NULL,
    paid_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',           -- pending | paid | failed
    bank_transaction_ref VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 한 settlement는 보통 한 payout (1:1)이지만, 분할 지급의 경우 1:N도 가능.
CREATE INDEX idx_payouts_settlement ON payouts (settlement_id);

-- ============================================================
-- settlement_failures — 실패 정산 추적
-- ============================================================
CREATE TABLE settlement_failures (
    id UUID PRIMARY KEY,
    settlement_id UUID NOT NULL REFERENCES settlements(id),
    failed_at TIMESTAMPTZ NOT NULL,
    reason VARCHAR(500),
    retry_count INTEGER NOT NULL DEFAULT 0,
    resolved_at TIMESTAMPTZ
);
