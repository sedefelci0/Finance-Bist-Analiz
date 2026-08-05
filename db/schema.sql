-- BIST Finansal Analiz Aracı — MVP şeması
-- financial_statements: normalize edilmiş, kaynağı belli, ne zaman çekildiği belli, append-only log.
-- Restatement (finansal tabloların sonradan düzeltilmesi) ihtimaline karşı satırlar
-- ÜZERİNE YAZILMAZ; aynı (ticker, period_date, metric_name) için birden fazla fetched_at
-- olabilir, en güncel değer sorgu tarafında seçilir.

CREATE TABLE IF NOT EXISTS financial_statements (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    period_date DATE NOT NULL,          -- verinin ait olduğu dönem sonu (örn. 2025-12-31)
    metric_name VARCHAR(64) NOT NULL,   -- normalizer'ın ürettiği kanonik alan adı (bkz. providers/normalizer.py)
    value NUMERIC,
    source VARCHAR(16) NOT NULL,        -- 'yfinance' | 'kap'
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()  -- verinin çekildiği an (as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_financial_statements_lookup
    ON financial_statements (ticker, period_date, metric_name, fetched_at DESC);

CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    calculation_date DATE NOT NULL,
    criterion_name VARCHAR(64) NOT NULL,
    criterion_score SMALLINT,           -- 1 = kriter sağlandı, 0 = sağlanmadı, NULL = veri yok
    total_score SMALLINT NOT NULL,      -- o hesaplama koşusunun toplam skoru (her satırda tekrarlanır)
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_scores_lookup
    ON scores (ticker, calculation_date);

-- pillar_scores: Alpha Score v2 (4 pillar + momentum filtresi) sonuçları.
-- "scores" tablosuyla AYNI değil, bilinçli olarak ayrı: scores kriter
-- bazlı (Piotroski'nin 9 alt kriteri) satırlar tutuyor, pillar_scores ise
-- pillar bazlı (4 satır + üstteki total_score/momentum_flag) satırlar
-- tutuyor — iki farklı granülerlik aynı tabloda karışırsa sorgulamak
-- karışır. scripts/calculate_score.py (salt F-Score) hâlâ "scores"
-- tablosunu kullanıyor; scripts/calculate_alpha_score.py bu tabloyu kullanıyor.
CREATE TABLE IF NOT EXISTS pillar_scores (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    calculation_date DATE NOT NULL,
    pillar_name VARCHAR(32) NOT NULL,   -- 'profitability' | 'safety' | 'valuation' | 'size'
    pillar_score NUMERIC,               -- 0-100, NULL = pillar hiç hesaplanamadı
    pillar_weight NUMERIC NOT NULL,     -- o pillar'ın ağırlığı (örn. 0.35)
    total_score NUMERIC,                -- o hesaplama koşusunun toplam skoru (her satırda tekrarlanır)
    momentum_flag BOOLEAN,              -- True = "momentum zayıf" uyarısı (skoru etkilemez)
    notes TEXT,
    period_date DATE                    -- Kârlılık/Sağlamlık'ın dayandığı mali dönem sonu (örn. 2024-12-31).
                                         -- Değerleme/Büyüklük anlık piyasa verisine dayandığı için bu satırlarda
                                         -- NULL kalabilir — bkz. scoring/pillars.py::_INSTANT_DATA_NOTE.
);

-- Tablo daha önce (bu kolon olmadan) oluşturulmuş olabilir — CREATE TABLE IF
-- NOT EXISTS var olan tabloyu değiştirmez, mevcut deployment'ları göçürmek
-- (migration) için ayrıca bu ALTER gerekiyor. Kolon zaten varsa no-op'tur.
ALTER TABLE pillar_scores ADD COLUMN IF NOT EXISTS period_date DATE;

CREATE INDEX IF NOT EXISTS idx_pillar_scores_lookup
    ON pillar_scores (ticker, calculation_date);
