"""İki kademeli veri toplama: önce yfinance, eksik kalemler için KAP fallback.

Mimari: Data Provider (yfinance_provider, kap_provider) -> Normalizer (bu modül)
-> Database. Normalizer hiçbir sağlayıcının iç detayını bilmez, sadece ortak
kanonik alan adları (net_income, total_assets, ...) üzerinden birleştirir.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

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

# KAP'ın "sirket-finansal-bilgileri" sayfasında bulunan (bkz. kap_provider.py
# _LABEL_CANDIDATES) akış/stok kalemleri — KAP KÖPRÜLEME (aşağıda) sadece
# bunlar için mümkün. operating_cash_flow, shares_outstanding,
# retained_earnings, invested_capital, tax_rate_for_calcs KAP'ta YOK —
# bunlar köprülenemez, yfinance'in en güncel (bridge edilmemiş) çeyreğinde kalır.
_KAP_TTM_FLOW_METRICS = {"net_income", "revenue", "gross_profit", "ebit"}
_KAP_TTM_STOCK_METRICS = {
    "total_assets",
    "current_assets",
    "current_liabilities",
    "long_term_debt",
    "total_equity",
    "total_liabilities",
}

# yfinance'in en güncel yıllık döneminin "bayat" sayılması için eşik — yıllık
# raporlar genelde dönem sonundan birkaç ay sonra yayınlanır, ~13 ay güvenli
# bir tolerans. Bu eşiğin üzerindeyse yfinance'in o dönemi TÜM alanları dolu
# olsa bile (bkz. get_financials'taki has_gaps mantığı) "eksik" sayılır ki
# KAP'ta yfinance'in hiç bilmediği DAHA YENİ bir dönem varsa (örn. yeni
# listelenmiş/az takip edilen bir şirkette yfinance yıllarca güncellenmeyebilir)
# gözden kaçmasın.
_STALE_ANNUAL_THRESHOLD_DAYS = 400


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
    #
    # ayrıca: yfinance'in bildiği en güncel dönem "bayat" (bkz.
    # _STALE_ANNUAL_THRESHOLD_DAYS) ise de KAP'a bakılır — yoksa yfinance'in
    # SAHİP OLDUĞU eski dönemlerin tüm alanları dolu diye (görünürde "eksik
    # yok"), KAP'ta yfinance'in hiç bilmediği daha yeni bir dönem (örn. az
    # takip edilen bir şirkette yfinance yıllarca güncellenmemiş olabilir)
    # sessizce gözden kaçar — kullanıcı gerçekte 2 yıl önceki kâr rakamlarını
    # "güncel" sanır.
    yf_latest_period = max(yf_metrics.keys()) if yf_metrics else None
    is_stale = yf_latest_period is None or (
        (date.today() - yf_latest_period).days > _STALE_ANNUAL_THRESHOLD_DAYS
    )
    has_gaps = (
        is_stale
        or any(
            period_metrics.get(metric) is None
            for period_metrics in yf_metrics.values()
            for metric in CANONICAL_METRICS
        )
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


def _try_kap_bridge(
    ticker: str, quarterly: dict[date, dict[str, float | None]], yf_latest_date: date
) -> tuple[date, dict[str, float | None]] | None:
    """KAP'ta yfinance'in en güncel çeyreğinden DAHA YENİ bir kümülatif ara
    dönem varsa (örn. KAP'ta 2026/06 ama yfinance hâlâ 2026/03'te), gerçek
    TTM'i KAP'ın taze verisiyle "köprüler".

    NEDEN GEREKLİ: KAP resmi/zorunlu açıklama platformu olduğu için yfinance'ten
    (özellikle gelişen piyasa hisselerinde) günler/haftalar önce güncellenebiliyor
    (kullanıcı gözlemi: TUPRS Q2 2026 sonuçlarını KAP'ta paylaştı ama yfinance
    hâlâ Q1'de takılıydı). KAP'ın ara dönem sütunu KÜMÜLATİF (Ocak'tan o aya
    kadar toplam) olduğu için, gerçek (12 aylık kayan) TTM'i türetmek için:

        TTM = TamYıl(Y-1) - AynıDönemKümülatif(Y-1) + KAP'ınEnGüncelKümülatifi(Y)

    "AynıDönemKümülatif(Y-1)" KAP'ın bu sayfasında YOK (sadece son dönem
    gösteriliyor) — bunu yfinance'in AYRIK çeyreklerinden kendimiz topluyoruz
    (örn. Y-1'in Ocak-Haziran'ı = yfinance'in Y-1 Ç1 + Y-1 Ç2 çeyrekleri).
    Bu iki kaynağın da (KAP kümülatifi, yfinance'in ayrık çeyrekleri) TUTARLI
    (aynı para birimi, aynı muhasebe standardı) olduğu tek durum
    financialCurrency TRY olan tickerlar — çağıran taraf (get_ttm_financials)
    zaten bunu garanti ediyor (aksi halde `quarterly` boş gelir).

    Dönüş: (bridge_period_end, {"net_income": ..., "total_assets": ..., ...})
    veya köprüleme mümkün değilse None (örn. gerekli tüm parçalar yoksa —
    o zaman get_ttm_financials sessizce plain yfinance TTM'e döner).
    """
    try:
        kap_all = kap_provider.fetch_all_periods_financials(ticker)
    except Exception:
        return None
    if not kap_all:
        return None

    kap_latest_date = max(kap_all.keys())
    if kap_latest_date <= yf_latest_date or kap_latest_date.month == 12:
        # KAP zaten yfinance'ten güncel değil, ya da KAP'ın en güncel dönemi
        # zaten yıl sonu (bu durumda köprülemeye gerek yok — get_financials'ın
        # yıllık verisiyle zaten örtüşür).
        return None

    y, m = kap_latest_date.year, kap_latest_date.month
    fy_prev_date = date(y - 1, 12, 31)
    kap_fy_prev = kap_all.get(fy_prev_date)
    kap_latest = kap_all.get(kap_latest_date)
    if kap_fy_prev is None or kap_latest is None:
        return None

    # Bir önceki yılın AYNI noktaya kadarki kümülatifini yfinance'in ayrık
    # çeyreklerinden kendimiz topluyoruz — 3, 6 veya 9. ay sonu çeyreklerinin
    # HEPSİ mevcut olmalı, biri bile eksikse köprüleme güvenilir olmaz.
    required_quarter_ends = [date(y - 1, mm, calendar.monthrange(y - 1, mm)[1]) for mm in range(3, m, 3)] + [
        date(y - 1, m, calendar.monthrange(y - 1, m)[1])
    ]
    prior_year_quarters = [quarterly.get(d) for d in required_quarter_ends]
    if any(q is None for q in prior_year_quarters):
        return None

    bridged: dict[str, float | None] = {}
    for metric in _KAP_TTM_FLOW_METRICS:
        fy_val = kap_fy_prev.get(metric)
        latest_val = kap_latest.get(metric)
        prior_partial_vals = [q.get(metric) for q in prior_year_quarters]
        if fy_val is None or latest_val is None or any(v is None for v in prior_partial_vals):
            continue
        bridged[metric] = fy_val - sum(prior_partial_vals) + latest_val

    if not bridged:
        return None

    for metric in _KAP_TTM_STOCK_METRICS:
        value = kap_latest.get(metric)
        if value is not None:
            bridged[metric] = value

    return kap_latest_date, bridged


def get_ttm_financials(
    ticker: str,
) -> tuple[dict[str, float | None], dict[str, str], list[date]]:
    """TTM (Trailing Twelve Months — kayan son 12 ay) sentetik dönem üretir.

    AKIŞ kalemleri (_TTM_FLOW_METRICS) son 4 çeyreğin TOPLAMI; geri kalan
    (bilanço/stok kalemleri + tax_rate_for_calcs) EN SON çeyreğin anlık
    değeri — TTM hesaplamasının standart yöntemi. Bu, YFINANCE'İN AYRIK
    çeyreklerinden hesaplanır.

    KAP KÖPRÜLEME: yfinance'in çeyreklik verisi (özellikle gelişen piyasa
    hisselerinde) haftalarca gecikebiliyor — KAP resmi platform olduğu için
    genelde daha güncel. KAP'ta yfinance'ten daha yeni bir kümülatif ara
    dönem varsa, _try_kap_bridge() gerçek TTM'i o taze veriyle günceller
    (bkz. o fonksiyonun docstring'i — matematiği ve neden güvenli olduğu
    orada anlatılıyor). Köprüleme başarısız/mümkün değilse (örn. gerekli
    ara çeyrekler eksik, ya da financialCurrency TRY değil) sessizce plain
    yfinance TTM'e dönülür — hiçbir zaman yarım/riskli bir köprüleme
    sonucu döndürülmez.

    NOT: KAP'ta operating_cash_flow, shares_outstanding, retained_earnings,
    invested_capital, tax_rate_for_calcs YOK — bu kalemler köprülenemez,
    her zaman yfinance'in (bridge edilmemiş) en güncel çeyreğinde kalır.

    Dönüş: (metrics, sources, window_dates)
      metrics[metric_name] -> değer ya da None (DÜZ dict — get_financials'ın
        aksine TEK bir sentetik dönemi temsil ettiği için dict[date,...] değil)
      sources[metric_name] -> "yfinance" | "kap_koprulenmis" | "yok"
      window_dates: [pencere_başlangıcı, pencere_bitişi] — notes'ta "TTM
        (2025-07-01 - 2026-06-30)" gibi şeffaflık için (bkz.
        scoring/pillars.py::_period_prefix).
    """
    # fetch_quarterly_financials bazen tamamen boş (NaN) bir "trailing" kolon
    # döndürebiliyor (bkz. o fonksiyonun docstring'i) — daha fazla isteyip
    # gerçekten dolu olanları seçerek bu sorunu bertaraf ediyoruz. 8 çeyrek
    # (2 yıl) isteniyor çünkü KAP köprüleme bir önceki yılın ara dönem
    # çeyreklerine de ihtiyaç duyabiliyor.
    quarterly = yfinance_provider.fetch_quarterly_financials(ticker, quarters=8)

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
    yf_latest_date = last_4[0][0]
    yf_oldest_included = last_4[-1][0]

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

    window_end = yf_latest_date
    window_start = yf_oldest_included

    bridge = _try_kap_bridge(ticker, quarterly, yf_latest_date)
    if bridge is not None:
        bridge_date, bridged_metrics = bridge
        for metric, value in bridged_metrics.items():
            metrics[metric] = value
            sources[metric] = "kap_koprulenmis"
        window_end = bridge_date
        window_start = date(bridge_date.year - 1, bridge_date.month, bridge_date.day) + timedelta(days=1)

    return metrics, sources, [window_start, window_end]


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
