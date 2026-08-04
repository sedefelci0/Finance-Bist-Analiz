"""yfinance üzerinden BIST hissesi için yıllık finansal tablo kalemlerini çeker.

Sadece ham veriyi çeker ve yfinance'in kendi satır etiketleriyle (Total Assets,
Net Income, ...) bir sözlük döndürür. Kanonik alan adlarına çevirme işi
providers/normalizer.py içinde yapılır — bu modül tek bir kaynağı bilir, KAP'tan
haberi yoktur (mimaride her provider bağımsız bir modül olsun kuralı).
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import yfinance as yf

# yfinance'in aynı kalemi farklı yfinance sürümlerinde/şirketlerinde farklı
# etiketlerle döndürebildiği durumlar için, her kanonik alan için birden fazla
# olası etiket deniyoruz (ilk bulunan kullanılır).
_LABEL_CANDIDATES: dict[str, list[str]] = {
    "net_income": ["Net Income", "Net Income Common Stockholders"],
    "total_assets": ["Total Assets"],
    "current_assets": ["Current Assets", "Total Current Assets"],
    "current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
    "long_term_debt": ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"],
    "gross_profit": ["Gross Profit"],
    "revenue": ["Total Revenue", "Operating Revenue"],
    "shares_outstanding": ["Share Issued", "Ordinary Shares Number"],
    "operating_cash_flow": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    # Alpha Score v2 (Pillar 1 kârlılık + Pillar 2 Altman Z-Score) için eklendi:
    "ebit": ["EBIT"],
    "retained_earnings": ["Retained Earnings"],  # KAP'ın özet bilanço görünümünde YOK, sadece yfinance
    "total_equity": ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"],
    "total_liabilities": ["Total Liabilities Net Minority Interest"],
    "invested_capital": ["Invested Capital"],  # KAP'ta YOK, sadece yfinance — ROIC hesabı için
    "tax_rate_for_calcs": ["Tax Rate For Calcs"],  # KAP'ta YOK, sadece yfinance — ROIC (NOPAT) için
}


def _find_row(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    for label in candidates:
        if label in df.index:
            return df.loc[label]
    return None


def fetch_annual_financials(ticker: str, years: int = 2) -> dict[date, dict[str, float | None]]:
    """Belirtilen ticker için son `years` yıllık finansal kalemleri çeker.

    Dönüş: {period_date: {"net_income": ..., "total_assets": ..., ...}, ...}
    Bulunamayan kalemler None olarak bırakılır (normalizer/KAP fallback bunları tamamlar).

    ÖNEMLİ: yfinance bazı BIST şirketleri için finansal tabloları TRY yerine
    USD cinsinden raporluyor (örn. THYAO.IS: info["financialCurrency"] == "USD",
    KAP her zaman TRY kullanır). Bu, aynı dönem için yfinance ve KAP kalemlerini
    birlikte kullanırsanız (örn. net_income USD'den, total_assets TRY'den) ROA
    gibi oranları ~30-40x yanlış hesaplar. Bu yüzden financialCurrency TRY
    değilse burada TÜM veri reddediliyor (boş dönüyor) ki normalizer o dönem
    için tamamen KAP'a (tutarlı TRY) düşsün — kısmi/karışık kaynak riski yok.
    """
    t = yf.Ticker(ticker)

    financial_currency = t.info.get("financialCurrency")
    if financial_currency and financial_currency != "TRY":
        return {}

    balance_sheet = t.balance_sheet          # yıllık bilanço
    income_stmt = t.financials                # yıllık gelir tablosu
    cash_flow = t.cashflow                     # yıllık nakit akış tablosu

    # Üç tablonun da ortak olarak sahip olduğu dönem (kolon) sonu tarihlerini al.
    period_ends: list[pd.Timestamp] = []
    for df in (balance_sheet, income_stmt, cash_flow):
        if df is not None and not df.empty:
            period_ends.extend(df.columns.tolist())
    period_ends = sorted(set(period_ends), reverse=True)[:years]

    results: dict[date, dict[str, float | None]] = {}
    for period_end in period_ends:
        period_date = period_end.date() if hasattr(period_end, "date") else period_end
        metrics: dict[str, float | None] = {}
        for metric_name, candidates in _LABEL_CANDIDATES.items():
            value = None
            for df in (balance_sheet, income_stmt, cash_flow):
                if df is None or df.empty or period_end not in df.columns:
                    continue
                row = _find_row(df, candidates)
                if row is not None and period_end in row.index:
                    raw = row[period_end]
                    if pd.notna(raw):
                        value = float(raw)
                        break
            metrics[metric_name] = value
        results[period_date] = metrics

    return results


def fetch_market_data(ticker: str) -> dict:
    """Anlık (point-in-time) piyasa verisi: market cap, beta, çarpanlar, sektör.

    financial_statements gibi dönemsel bir tablo DEĞİL — bu "şu an" geçerli
    tek bir enstantane, o yüzden DB'ye ayrı bir yapıda yazılmıyor, pillar
    hesaplamalarında doğrudan bellekte kullanılıyor.

    DİKKAT: PE/PEG/P-B/EV-EBITDA gibi çarpanlar hem fiyata (her zaman TRY,
    borsanın işlem para birimi) hem kazanç/defter değerine (financialCurrency
    USD ise USD) dayanır. financialCurrency != currency olan tickerlarda bu
    çarpanlar farklı para birimlerinin karışımı olabilir — `currency_mismatch`
    alanı bunu işaretler, kullanan taraf (valuation pillar) buna göre uyarı
    ekleyebilir.
    """
    info = yf.Ticker(ticker).info
    currency = info.get("currency")
    financial_currency = info.get("financialCurrency")
    return {
        "market_cap": info.get("marketCap"),
        "beta": info.get("beta"),
        "trailing_pe": info.get("trailingPE"),
        "peg_ratio": info.get("pegRatio"),
        "price_to_book": info.get("priceToBook"),
        "ev_to_ebitda": info.get("enterpriseToEbitda"),
        "sector": info.get("sector"),
        "currency_mismatch": bool(financial_currency and currency and financial_currency != currency),
    }


def fetch_price_returns(ticker: str) -> dict[str, float | None]:
    """Momentum filtresi için son 6 ve 12 aylık toplam getiri (%).

    Fiyat verisi (yfinance history) financialCurrency sorunundan etkilenmez —
    her zaman borsanın işlem para birimiyle (TRY) gelir.
    """
    hist = yf.Ticker(ticker).history(period="13mo", interval="1d", auto_adjust=True)
    if hist.empty:
        return {"return_6m": None, "return_12m": None}

    last_price = float(hist["Close"].iloc[-1])
    last_date = hist.index[-1]

    def _return_since(months_ago: int) -> float | None:
        target = last_date - pd.DateOffset(months=months_ago)
        past = hist.loc[hist.index <= target]
        if past.empty:
            return None
        past_price = float(past["Close"].iloc[-1])
        if past_price == 0:
            return None
        return (last_price / past_price - 1) * 100

    return {"return_6m": _return_since(6), "return_12m": _return_since(12)}
