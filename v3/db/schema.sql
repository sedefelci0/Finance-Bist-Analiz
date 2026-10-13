-- v3 ham finansal tablo şeması — Neon "v3-dev" branch'i için (kullanıcı kararı, 13 Ekim).
-- Canlı v2 veritabanına UYGULANMAZ. Henüz hiçbir yere uygulanmadı.
-- Ham sağlayıcı verisi yalnızca veritabanında tutulur, repoya girmez.

-- Her çekim denemesi sonucu: ne zaman, nereden, hangi parametreyle, sonuç ne oldu.
CREATE TABLE IF NOT EXISTS raw_fetch (
    fetch_id        BIGSERIAL PRIMARY KEY,
    ticker          TEXT        NOT NULL,
    source          TEXT        NOT NULL,             -- kaynak adı (karar bekliyor: kap / isyatirim / yfinance)
    source_group    TEXT,                              -- kaynağa özgü tablo grubu (ör. XI_29, UFRS_K, ifrs_standard, bddk)
    request_params  JSONB       NOT NULL,              -- istenen dönemler vb.
    status          TEXT        NOT NULL CHECK (status IN ('ok', 'kaynakta_yok', 'hata')),
    attempts        INT         NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    item_count      INT,
    error           TEXT,
    payload_sha256  TEXT,                              -- aynı cevap tekrar geldi mi
    payload         JSONB                              -- ham cevap, olduğu gibi
);
CREATE INDEX IF NOT EXISTS raw_fetch_lookup ON raw_fetch (source, ticker, status);

-- Kalem bazında ham değer (hesaplama yok).
CREATE TABLE IF NOT EXISTS raw_statement_item (
    fetch_id              BIGINT  NOT NULL REFERENCES raw_fetch (fetch_id),
    ticker                TEXT    NOT NULL,
    source                TEXT    NOT NULL,
    period_end            DATE    NOT NULL,
    period_type           TEXT    NOT NULL CHECK (period_type IN ('Q', 'A')),
    is_cumulative         BOOLEAN NOT NULL,           -- kümülatif ara dönem mi (İş/KAP: evet, yfinance: hayır)
    consolidated          BOOLEAN,
    item_code             TEXT    NOT NULL,           -- kaynağın kalem kodu ya da satır adı
    item_name             TEXT,
    value                 NUMERIC,
    currency              TEXT    NOT NULL,           -- TRY / USD
    unit_scale            INT     NOT NULL DEFAULT 1, -- 1 / 1000 / 1000000
    purchasing_power_date DATE,                        -- TMS 29 birim tarihi; çekimde BOŞ, birim kuralı doldurur
    PRIMARY KEY (fetch_id, period_end, period_type, item_code)
);

-- Bilanço açıklanma tarihi (yeniden çekme tetikleyicisi + backtest için).
CREATE TABLE IF NOT EXISTS statement_disclosure (
    ticker        TEXT NOT NULL,
    period_end    DATE NOT NULL,
    disclosed_at  TIMESTAMPTZ,
    source        TEXT,                                -- kap / elle
    kap_ref       TEXT,
    PRIMARY KEY (ticker, period_end)
);

-- Hisse bazında hangi kaynak seçildi ve neden (tek kaynak kuralı).
CREATE TABLE IF NOT EXISTS source_choice (
    ticker         TEXT        NOT NULL,
    period_end     DATE        NOT NULL,
    chosen_source  TEXT        NOT NULL,
    reason         TEXT        NOT NULL,
    decided_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    score_version  TEXT        NOT NULL DEFAULT 'v3',
    PRIMARY KEY (ticker, period_end, score_version)
);

-- Evren üyeliği tarih damgasıyla (BIST100 önceliği, seçenek A; backtest için geçmiş üyelik).
CREATE TABLE IF NOT EXISTS universe_member (
    snapshot_date DATE    NOT NULL,                    -- CSV'deki tarih
    index_code    TEXT    NOT NULL,                    -- ayar: XYLDZ
    ticker        TEXT    NOT NULL,
    in_xu100      BOOLEAN NOT NULL,                    -- yalnızca dolum önceliği
    PRIMARY KEY (snapshot_date, index_code, ticker)
);
