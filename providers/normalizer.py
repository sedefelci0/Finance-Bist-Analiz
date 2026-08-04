"""İki kademeli veri toplama: önce yfinance, eksik kalemler için KAP fallback.

Mimari: Data Provider (yfinance_provider, kap_provider) -> Normalizer (bu modül)
-> Database. Normalizer hiçbir sağlayıcının iç detayını bilmez, sadece ortak
kanonik alan adları (net_income, total_assets, ...) üzerinden birleştirir.
"""
from __future__ import annotations

from datetime import date

from providers import kap_provider, yfinance_provider

CANONICAL_METRICS = [
    "net_income",
    "total_assets",
    "current_assets",
    "current_liabilities",
    "long_term_debt",
    "gross_profit",
    "revenue",
    "operating_cash_flow",
    "shares_outstanding",
    # Alpha Score v2 (Altman Z-Score + ROE/ROIC) için eklendi — KAP'ta
    # bulunmayanlar (retained_earnings, invested_capital, tax_rate_for_calcs)
    # için tek kaynak yfinance'tir, bkz. kap_provider.py NOT.
    "ebit",
    "retained_earnings",
    "total_equity",
    "total_liabilities",
    "invested_capital",
    "tax_rate_for_calcs",
]


def get_financials(
    ticker: str, years: int = 2
) -> tuple[dict[date, dict[str, float | None]], dict[date, dict[str, str]]]:
    """Ticker için son `years` yıllık finansal kalemleri döndürür.

    Dönüş: (metrics, sources)
      metrics[period_date][metric_name] -> değer ya da None (hiçbir kaynakta yoksa)
      sources[period_date][metric_name] -> "yfinance" | "kap" | "yok"
    """
    yf_metrics = yfinance_provider.fetch_annual_financials(ticker, years=years)

    # yfinance tamamen boş dönebilir (örn. financialCurrency TRY değilse —
    # bkz. yfinance_provider docstring) ya da bazı dönemler/kalemler eksik
    # olabilir. Her iki durumda da KAP'ı önceden çekiyoruz ki dönem kümesini
    # SADECE yfinance'in bildiği dönemlerle sınırlamayalım (yfinance boşsa
    # hangi dönemlere ihtiyacımız olduğunu bilemeyiz).
    has_gaps = not yf_metrics or any(
        period_metrics.get(metric) is None
        for period_metrics in yf_metrics.values()
        for metric in CANONICAL_METRICS
    )

    kap_metrics: dict[date, dict[str, float | None]] = {}
    if has_gaps:
        try:
            kap_metrics = kap_provider.fetch_annual_financials(ticker)
        except Exception:
            # KAP erişilemezse (site yapısı değişti, ağ hatası, vb.) sessizce
            # atla — bu kalemler "yok" olarak işaretli kalır, script çökmez.
            kap_metrics = {}

    all_period_dates = sorted(set(yf_metrics) | set(kap_metrics), reverse=True)[:years]

    metrics: dict[date, dict[str, float | None]] = {}
    sources: dict[date, dict[str, str]] = {}
    for period_date in all_period_dates:
        metrics[period_date] = {}
        sources[period_date] = {}
        for metric in CANONICAL_METRICS:
            yf_value = yf_metrics.get(period_date, {}).get(metric)
            if yf_value is not None:
                metrics[period_date][metric] = yf_value
                sources[period_date][metric] = "yfinance"
                continue
            kap_value = kap_metrics.get(period_date, {}).get(metric)
            if kap_value is not None:
                metrics[period_date][metric] = kap_value
                sources[period_date][metric] = "kap"
                continue
            metrics[period_date][metric] = None
            sources[period_date][metric] = "yok"

    return metrics, sources


def to_flat_rows(
    metrics: dict[date, dict[str, float | None]], sources: dict[date, dict[str, str]]
) -> list[dict]:
    """db.connection.save_financial_metrics'in beklediği düz satır listesine çevirir."""
    rows = []
    for period_date, period_metrics in metrics.items():
        for metric_name, value in period_metrics.items():
            source = sources.get(period_date, {}).get(metric_name, "yok")
            if source == "yok":
                continue  # hiçbir kaynakta olmayan kalemi DB'ye yazmaya gerek yok
            rows.append(
                {
                    "period_date": period_date,
                    "metric_name": metric_name,
                    "value": value,
                    "source": source,
                }
            )
    return rows
