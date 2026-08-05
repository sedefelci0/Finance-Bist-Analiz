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

# TTM (Trailing Twelve Months) hesabında AKIŞ kalemleri son 4 çeyrek TOPLANIR;
# geri kalanı (bilanço/stok kalemleri + tax_rate_for_calcs) TOPLANMAZ, en son
# çeyreğin anlık değeri kullanılır — bkz. get_ttm_financials.
_TTM_FLOW_METRICS = {"net_income", "revenue", "gross_profit", "operating_cash_flow", "ebit"}


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


def get_ttm_financials(
    ticker: str,
) -> tuple[dict[str, float | None], dict[str, str], list[date]]:
    """TTM (Trailing Twelve Months — kayan son 12 ay) sentetik dönem üretir.

    AKIŞ kalemleri (_TTM_FLOW_METRICS: net_income, revenue, gross_profit,
    operating_cash_flow, ebit) son 4 çeyreğin TOPLAMI; geri kalan (bilanço/
    stok kalemleri + tax_rate_for_calcs) EN SON çeyreğin anlık değeri —
    TTM hesaplamasının standart yöntemi.

    KAP FALLBACK YOK: KAP'ın finansal bilgi sayfası yıl sonu (Aralık) dışındaki
    ara dönemleri KÜMÜLATİF (Ocak-Mart, Ocak-Haziran, ...) veriyor, ayrık
    (discrete) çeyreklik değil — bunlardan doğru TTM üretmek için art arda
    çıkarma (örn. Q4 = tam yıl - 9 aylık kümülatif) gerekir; bu ekstra
    karmaşıklık ve farklı dönem tanımlarının karışma riski bilinçli olarak
    alınmadı. financialCurrency TRY olmayan (yfinance'in tamamen reddedildiği,
    bkz. yfinance_provider) tickerlarda TTM bu yüzden hep "veri yok" kalır —
    KAP'a düşülmez.

    Dönüş: (metrics, sources, quarter_dates)
      metrics[metric_name] -> değer ya da None (DÜZ dict — get_financials'ın
        aksine TEK bir sentetik dönemi temsil ettiği için dict[date,...] değil)
      sources[metric_name] -> "yfinance" | "yok"
      quarter_dates: TTM'e dahil edilen 4 çeyreğin dönem sonu tarihleri
        (en yeniden en eskiye) — notes'ta "TTM (2025/Q2 - 2026/Q1)" gibi
        şeffaflık için (bkz. scoring/pillars.py::_period_prefix).
    """
    # fetch_quarterly_financials bazen tamamen boş (NaN) bir "trailing" kolon
    # döndürebiliyor (bkz. o fonksiyonun docstring'i) — 4'ten fazla isteyip
    # gerçekten dolu olan ilk 4'ü seçerek bu sorunu bertaraf ediyoruz.
    quarterly = yfinance_provider.fetch_quarterly_financials(ticker, quarters=6)

    populated_quarters = [
        (period_date, period_metrics)
        for period_date, period_metrics in sorted(quarterly.items(), reverse=True)
        if any(period_metrics.get(m) is not None for m in _TTM_FLOW_METRICS)
    ]

    if len(populated_quarters) < 4:
        # Yeterli çeyrek yok (örn. financialCurrency TRY değil, ya da yeni
        # listelenmiş bir şirket) — TTM tamamen "veri yok".
        return (
            {metric: None for metric in CANONICAL_METRICS},
            {metric: "yok" for metric in CANONICAL_METRICS},
            [],
        )

    last_4 = populated_quarters[:4]
    latest_period_metrics = last_4[0][1]
    quarter_dates = [q[0] for q in last_4]

    metrics: dict[str, float | None] = {}
    sources: dict[str, str] = {}
    for metric in CANONICAL_METRICS:
        if metric in _TTM_FLOW_METRICS:
            values = [q_metrics.get(metric) for _, q_metrics in last_4]
            if all(v is not None for v in values):
                metrics[metric] = sum(values)
                sources[metric] = "yfinance"
            else:
                metrics[metric] = None
                sources[metric] = "yok"
        else:
            value = latest_period_metrics.get(metric)
            metrics[metric] = value
            sources[metric] = "yfinance" if value is not None else "yok"

    return metrics, sources, quarter_dates


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
