CREATE TABLE best_exchange_rates (
    firm VARCHAR(40),
    currency VARCHAR(10) PRIMARY KEY,
    best_buy_rate NUMERIC(18, 8) NOT NULL DEFAULT 0.0,
    best_sell_rate NUMERIC(18, 8) NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);