-- US Multifamily REIT & Rent Control Intelligence Engine
-- Market Intelligence Schema
-- Every row is fully auditable via exact_text_quote + source_url

CREATE TABLE IF NOT EXISTS market_intelligence (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    metro_market          TEXT    NOT NULL,
    state_code            TEXT    NOT NULL,
    tickers_exposed       TEXT    NOT NULL,
    category              TEXT    NOT NULL CHECK (category IN (
                              'Traditional Rent Cap',
                              'Algorithmic Pricing Ban',
                              'Ballot Initiative',
                              'Candidate Profiling'
                          )),
    state_of_law          TEXT    NOT NULL CHECK (state_of_law IN (
                              'Active Enforced',
                              'Pending Vote',
                              'Developing Ballot',
                              'Defeated/Preempted'
                          )),
    headline              TEXT    NOT NULL,
    summary_insight       TEXT,
    portfolio_risk_impact TEXT    NOT NULL CHECK (portfolio_risk_impact IN (
                              'Critical',
                              'Moderate',
                              'Low/Stable'
                          )),
    sentiment_score       REAL    NOT NULL CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    source_name           TEXT,
    source_url            TEXT,
    exact_text_quote      TEXT,
    last_updated          DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mi_state_category
    ON market_intelligence (state_code, category);

CREATE INDEX IF NOT EXISTS idx_mi_tickers
    ON market_intelligence (tickers_exposed);

CREATE INDEX IF NOT EXISTS idx_mi_risk
    ON market_intelligence (portfolio_risk_impact);
