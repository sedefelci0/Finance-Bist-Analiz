"""PostgreSQL bağlantısı ve şema/yazma yardımcıları.

Uygulama katmanı canlı API'lere değil sadece bu modül üzerinden veritabanına
bağlanır (bkz. proje mimarisi: Data Provider -> Normalizer -> Database -> Score Engine).
"""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_engine() -> Engine:
    """.env içindeki DB_* değişkenlerinden SQLAlchemy engine oluşturur.

    DB_SSLMODE (opsiyonel) Neon gibi SSL zorunlu koşan sağlayıcılar için —
    boşsa hiç eklenmez (yerel PostgreSQL'de genelde gerekmez).
    """
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "bist_analiz")
    user = quote_plus(os.environ.get("DB_USER", "postgres"))
    password = quote_plus(os.environ.get("DB_PASSWORD", ""))
    sslmode = os.environ.get("DB_SSLMODE")

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
) -> None:
    """Alpha Score v2 sonucunu pillar_scores tablosuna yazar.

    pillars: [{"name": str, "score": float | None, "weight": float, "notes": str}, ...]
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO pillar_scores
                    (ticker, calculation_date, pillar_name, pillar_score, pillar_weight,
                     total_score, momentum_flag, notes)
                VALUES
                    (:ticker, :calculation_date, :pillar_name, :pillar_score, :pillar_weight,
                     :total_score, :momentum_flag, :notes)
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
                }
                for p in pillars
            ],
        )
