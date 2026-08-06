"""PostgreSQL bağlantısı ve şema/yazma yardımcıları.

Uygulama katmanı canlı API'lere değil sadece bu modül üzerinden veritabanına
bağlanır (bkz. proje mimarisi: Data Provider -> Normalizer -> Database -> Score Engine).
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _get_config(key: str, default: str = "") -> str:
    """Önce Streamlit Cloud'un st.secrets'ına, yoksa ortam değişkenlerine (.env) bakar.

    CLI scriptleri (calculate_score.py vb.) streamlit kurulu olmadan da
    çalışabilmeli — bu yüzden streamlit importu try/except içinde, sert bir
    bağımlılık değil. Streamlit Cloud'daki "Secrets" TOML alanının os.environ'a
    otomatik yansıyıp yansımadığı belgelerde net değildi, bu fonksiyon o
    belirsizliği ortadan kaldırıyor.
    """
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def get_engine() -> Engine:
    """DB_* ayarlarından SQLAlchemy engine oluşturur (bkz. _get_config).

    DB_SSLMODE (opsiyonel) Neon gibi SSL zorunlu koşan sağlayıcılar için —
    boşsa hiç eklenmez (yerel PostgreSQL'de genelde gerekmez).
    """
    host = _get_config("DB_HOST", "localhost")
    port = _get_config("DB_PORT", "5432")
    name = _get_config("DB_NAME", "bist_analiz")
    user = quote_plus(_get_config("DB_USER", "postgres"))
    password = quote_plus(_get_config("DB_PASSWORD", ""))
    sslmode = _get_config("DB_SSLMODE")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    if sslmode:
        url += f"?sslmode={sslmode}"
    return create_engine(url)


def ensure_schema(engine: Engine) -> None:
    """db/schema.sql içindeki tabloları (yoksa) oluşturur.

    DDL'i Python tarafında ";" ile bölmüyoruz — yorum satırları içinde
    (örn. Türkçe cümlelerde noktalama olarak) ";" geçebiliyor ve naif bir
    split bunu yanlış statement sınırı sanıp "empty query" hatası veriyor.
    Bunun yerine tüm dosyayı TEK bir exec_driver_sql çağrısıyla gönderiyoruz;
    psycopg2/libpq çoklu ";"-ayrılmış komutları tek çağrıda native olarak
    çalıştırabiliyor, statement ayrıştırmasını veritabanının kendisine bırakır.
    """
    ddl = _SCHEMA_PATH.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(ddl)


def save_financial_metrics(engine: Engine, ticker: str, rows: list[dict]) -> None:
    """Normalizer'dan gelen metrikleri financial_statements tablosuna ekler.

    rows: [{"period_date": date, "metric_name": str, "value": float | None, "source": str}, ...]
    Append-only: aynı (ticker, period_date, metric_name) tekrar yazılırsa eski satır
    silinmez, yeni fetched_at ile yeni bir satır eklenir (point-in-time bütünlüğü).
    """
    if not rows:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO financial_statements
                    (ticker, period_date, metric_name, value, source, fetched_at)
                VALUES
                    (:ticker, :period_date, :metric_name, :value, :source, :fetched_at)
                """
            ),
            [
                {
                    "ticker": ticker,
                    "period_date": row["period_date"],
                    "metric_name": row["metric_name"],
                    "value": row["value"],
                    "source": row["source"],
                    "fetched_at": datetime.utcnow(),
                }
                for row in rows
            ],
        )


def save_score_result(
    engine: Engine,
    ticker: str,
    calculation_date: date,
    criteria: list[dict],
    total_score: int,
) -> None:
    """Piotroski sonucunu scores tablosuna yazar.

    criteria: [{"name": str, "score": 0 | 1 | None, "notes": str}, ...]
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO scores
                    (ticker, calculation_date, criterion_name, criterion_score, total_score, notes)
                VALUES
                    (:ticker, :calculation_date, :criterion_name, :criterion_score, :total_score, :notes)
                """
            ),
            [
                {
                    "ticker": ticker,
                    "calculation_date": calculation_date,
                    "criterion_name": c["name"],
                    "criterion_score": c["score"],
                    "total_score": total_score,
                    "notes": c["notes"],
                }
                for c in criteria
            ],
        )


def save_pillar_scores(
    engine: Engine,
    ticker: str,
    calculation_date: date,
    pillars: list[dict],
    total_score: float | None,
    momentum_flag: bool | None,
    period_date: date | None = None,
    profitability_signal: str | None = None,
) -> None:
    """Alpha Score v2 sonucunu pillar_scores tablosuna yazar.

    pillars: [{"name": str, "score": float | None, "weight": float, "notes": str,
               "f_score_detail": dict | None}, ...] — f_score_detail sadece
    "safety" satırında dolu olur (bkz. scoring/pillars.py::calculate_safety_pillar),
    diğer pillar'larda anahtar hiç yoksa None yazılır.
    period_date: Kârlılık/Sağlamlık'ın dayandığı mali dönem sonu (örn.
    2024-12-31) — calculation_date (script'in ÇALIŞTIĞI tarih) ile
    KARIŞTIRILMASIN. Değerleme/Büyüklük anlık piyasa verisine dayandığı için
    kavramsal olarak bu alana ait değil, ama şema tek satır tipi tuttuğundan
    (bkz. schema.sql) her satırda aynı period_date tekrarlanır — hangi
    pillar'ın gerçekten döneme, hangisinin anlık veriye dayandığı notes
    metninde açık (bkz. scoring/pillars.py::_INSTANT_DATA_NOTE).
    profitability_signal: scoring/pillars.py::calculate_profitability_signal'ın
    ürettiği "toparlanma/bozulma/stabil" mesajı — total_score gibi her
    satırda tekrarlanır.
    """
    # Bu run'ın TÜM satırları AYNI created_at değerini alıyor (veritabanının
    # kendi now()'ını her satır için ayrı ayrı çağırmasına GÜVENMİYORUZ) —
    # load_latest_pillar_scores (app.py) "MAX(created_at) per ticker" ile
    # tam olarak bu run'ı izole edebilsin diye. Aynı ticker aynı gün içinde
    # birden fazla kez çalıştırılırsa (calculation_date DATE hassasiyeti
    # bunu ayırt edemez) bu olmadan eski/yeni run'ların satırları karışırdı.
    run_timestamp = datetime.utcnow()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO pillar_scores
                    (ticker, calculation_date, pillar_name, pillar_score, pillar_weight,
                     total_score, momentum_flag, notes, period_date, profitability_signal,
                     f_score_detail, created_at)
                VALUES
                    (:ticker, :calculation_date, :pillar_name, :pillar_score, :pillar_weight,
                     :total_score, :momentum_flag, :notes, :period_date, :profitability_signal,
                     CAST(:f_score_detail AS jsonb), :created_at)
                """
            ),
            [
                {
                    "ticker": ticker,
                    "calculation_date": calculation_date,
                    "pillar_name": p["name"],
                    "pillar_score": p["score"],
                    "pillar_weight": p["weight"],
                    "total_score": total_score,
                    "momentum_flag": momentum_flag,
                    "notes": p["notes"],
                    "period_date": period_date,
                    "profitability_signal": profitability_signal,
                    # date/datetime alanları (period_date, prev_period_date) JSON'a
                    # gömülü — default=str ile ISO metne çeviriyoruz.
                    "f_score_detail": (
                        json.dumps(p["f_score_detail"], default=str)
                        if p.get("f_score_detail") is not None
                        else None
                    ),
                    "created_at": run_timestamp,
                }
                for p in pillars
            ],
        )
