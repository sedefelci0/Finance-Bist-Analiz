"""BIST hissesi için Piotroski F-Score hesaplar ve (opsiyonel olarak) veritabanına yazar.

Kullanım:
    python scripts/calculate_score.py TUPRS.IS
    python scripts/calculate_score.py TUPRS.IS THYAO.IS --skip-db   # DB'ye yazmadan sadece ekrana bas

Veri akışı: yfinance_provider -> (eksikler için) kap_provider -> normalizer -> piotroski -> db
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows konsolunda Türkçe karakterler için

from db import connection as db  # noqa: E402
from providers import normalizer  # noqa: E402
from scoring import piotroski  # noqa: E402


def _print_report(ticker: str, result: dict) -> None:
    print(f"\n=== {ticker} — Piotroski F-Score ({result['period_date']}) ===")
    for c in result["criteria"]:
        mark = "VERİ YOK" if c["score"] is None else str(c["score"])
        print(f"  [{mark}] {c['name']}: {c['notes']}")
    print(
        f"\n  TOPLAM: {result['total_score']}/{result['calculated_count']} "
        f"({result['unavailable_count']} kriter veri eksikliğinden hesaplanamadı)"
    )


def run(ticker: str, engine, skip_db: bool) -> None:
    print(f"{ticker}: yfinance'ten veri çekiliyor...")
    metrics, sources = normalizer.get_financials(ticker, years=2)

    kap_used = any(s == "kap" for period in sources.values() for s in period.values())
    if kap_used:
        print(f"{ticker}: bazı kalemler için KAP fallback kullanıldı.")

    result = piotroski.calculate_f_score(metrics)
    _print_report(ticker, result)

    if skip_db:
        return

    rows = normalizer.to_flat_rows(metrics, sources)
    db.save_financial_metrics(engine, ticker, rows)
    db.save_score_result(
        engine,
        ticker,
        calculation_date=date.today(),
        criteria=[{"name": c["name"], "score": c["score"], "notes": c["notes"]} for c in result["criteria"]],
        total_score=result["total_score"],
    )
    print(f"{ticker}: financial_statements ve scores tablolarına yazıldı.")


def main() -> None:
    parser = argparse.ArgumentParser(description="BIST hissesi için Piotroski F-Score hesaplar")
    parser.add_argument("tickers", nargs="+", help="Örn: TUPRS.IS THYAO.IS")
    parser.add_argument("--skip-db", action="store_true", help="Sadece ekrana bas, veritabanına yazma")
    args = parser.parse_args()

    engine = None
    if not args.skip_db:
        engine = db.get_engine()
        db.ensure_schema(engine)

    for ticker in args.tickers:
        try:
            run(ticker, engine, args.skip_db)
        except Exception as exc:
            print(f"{ticker}: HATA — {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
