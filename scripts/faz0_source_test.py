"""Faz 0 — veri kaynağı testi (docs/scoring-v3.md bölüm 11-12).

Üretim kodu DEĞİLDİR; v3 veri katmanı için kaynak seçimine kanıt toplar.

Ne yapar:
  1. Erişim testi: Borsa İstanbul evren CSV'si, İş Yatırım MaliTablo, KAP, Yahoo.
     (Aynı script GitHub Actions'ta da çalışır — bulut IP'lerinden erişim sorusu için.)
  2. 20 hisse için 7 kalemi (toplam varlık, özkaynak, net kâr, satış, işletme nakit
     akışı, faiz gideri, finansal borç) üç kaynaktan çeker:
       - isyatirimhisse (İş Yatırım MaliTablo)
       - borsapy (o da İş Yatırım MaliTablo — bağımsız kaynak değil, paket katmanı testi)
       - yfinance (Yahoo)
  3. Eksik oranı, kaynaklar arası fark, para birimi, en güncel dönemi özetler.

Kibarlık: her HTTP isteği/paket çağrısı arasında en az DELAY saniye beklenir. Hiçbir
kaynak resmi bir istek sınırı yayınlamıyor (bkz. LEARNING.md adım 0.3).

Kullanım:
  python scripts/faz0_source_test.py --out docs/faz0/local
  python scripts/faz0_source_test.py --out docs/faz0/actions --tickers THYAO,GARAN
"""
from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

DELAY = 3.0

TICKERS = [
    # belgede adı geçenler
    "THYAO", "ASELS", "TMSN", "GLRMK", "GARAN", "AKBNK", "AGESA", "ANHYT", "KCHOL", "SAHOL",
    # 2 GYO
    "EKGYO", "ISGYO",
    # diğer sektörlerden 8
    "BIMAS", "TUPRS", "EREGL", "FROTO", "TCELL", "ENKAI", "ULKER", "SISE",
]

ITEMS = ["total_assets", "equity", "net_income", "revenue", "ocf", "interest_expense", "financial_debt"]
FLOW_ITEMS = {"net_income", "revenue", "ocf", "interest_expense"}

# Hedef dönemler: son 5 çeyrek ve son 5 yıl (bkz. LEARNING.md adım 0.5)
QUARTERS = [(2026, 6), (2026, 3), (2025, 12), (2025, 9), (2025, 6)]
YEARS = [2025, 2024, 2023, 2022, 2021]

ISY_URL = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
BIST_CSV_URL = "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"

# İş Yatırım kalem kodları — .faz0/probe_*.txt ham çıktılarından okundu.
# Kod listesi toplanır (ör. kısa + uzun vadeli finansal borç). None = bu ailede kalem yok.
ISY_CODES = {
    "industrial": {  # XI_29 — sanayi, holding, GYO
        "total_assets": ["1BL"],
        "equity": ["2N"],             # toplam özkaynak (azınlık dahil)
        "net_income": ["3Z"],         # ana ortaklık payı
        "revenue": ["3C"],
        "ocf": ["4C"],
        "interest_expense": ["4BB"],  # "Finansman Giderleri" — saf faizden geniş olabilir
        "financial_debt": ["2AA", "2BA"],
    },
    "bank": {  # UFRS, 2A = MEVDUAT
        "total_assets": ["1Z"],
        "equity": ["2O"],
        "net_income": ["3Z"],
        "revenue": None,              # bankada "satış" yok
        "ocf": None,                  # tabloda nakit akışı bölümü yok
        "interest_expense": ["3B"],   # FAİZ GİDERLERİ (mevduat faizi dahil — sanayiyle aynı anlamda değil)
        "financial_debt": None,       # mevduat finansal borç sayılmaz
    },
    "insurance": {  # UFRS, sigorta/emeklilik formatı
        "total_assets": ["1Z"],
        "equity": ["2O"],
        "net_income": ["3Z"],
        "revenue": None,              # prim ≠ satış; tanım kararı gerekiyor
        "ocf": None,
        "interest_expense": None,
        "financial_debt": ["2A", "2J"],
    },
}

# borsapy satırları itemDescTr ile indeksliyor (kod yok). Aynı adlı satırlar
# (ör. iki "Finansal Borçlar") çakışıyor — bu da bir bulgu, ayrıca raporlanır.
BPY_ROWS = {
    "industrial": {
        "total_assets": ("balance_sheet", ["TOPLAM VARLIKLAR"]),
        "equity": ("balance_sheet", ["Özkaynaklar"]),
        "net_income": ("income_stmt", ["Ana Ortaklık Payları"]),
        "revenue": ("income_stmt", ["Satış Gelirleri"]),
        "ocf": ("cashflow", ["İşletme Faaliyetlerinden Kaynaklanan Net Nakit"]),
        "interest_expense": ("cashflow", ["Finansman Giderleri"]),
        "financial_debt": ("balance_sheet", ["Finansal Borçlar"]),
    },
    "bank": {
        "total_assets": ("balance_sheet", ["AKTİF TOPLAMI"]),
        "equity": ("balance_sheet", ["XVI. ÖZKAYNAKLAR"]),
        "net_income": ("income_stmt", ["XXIII. NET DÖNEM KARI/ZARARI (XVII+XXII)"]),
        "interest_expense": ("income_stmt", ["II. FAİZ GİDERLERİ"]),
    },
    "insurance": {
        "total_assets": ("balance_sheet", ["AKTİF TOPLAMI"]),
        "equity": ("balance_sheet", ["Özsermaye Toplamı"]),
        "net_income": ("income_stmt", ["N- Dönem Net Karı veya Zararı"]),
        "financial_debt": ("balance_sheet", ["A- Finansal Borçlar"]),
    },
}

YF_ROWS = {
    "total_assets": ("balance", ["Total Assets"]),
    "equity": ("balance", ["Total Equity Gross Minority Interest", "Stockholders Equity"]),
    "net_income": ("income", ["Net Income Common Stockholders", "Net Income"]),
    "revenue": ("income", ["Total Revenue", "Operating Revenue"]),
    "ocf": ("cashflow", ["Operating Cash Flow"]),
    "interest_expense": ("income", ["Interest Expense", "Interest Expense Non Operating"]),
    "financial_debt": ("balance", ["Total Debt"]),
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def pause() -> None:
    time.sleep(DELAY)


# ---------------------------------------------------------------- erişim testi
def connectivity_check() -> list[dict]:
    """Her kaynağa tek, küçük bir istek. Hata sessizce yutulmaz, kaydedilir."""
    checks = [
        ("borsa_istanbul_csv", "GET", BIST_CSV_URL, None),
        ("isyatirim_malitablo", "GET", ISY_URL, dict(
            companyCode="THYAO", exchange="TRY", financialGroup="XI_29",
            year1=2026, period1=6, year2=2026, period2=3, year3=2025, period3=12, year4=2025, period4=9)),
        ("kap_home", "GET", "https://www.kap.org.tr/tr/", None),
        ("kap_company_list", "GET", "https://www.kap.org.tr/tr/bist-sirketler", None),
        ("yahoo_chart", "GET", "https://query1.finance.yahoo.com/v8/finance/chart/THYAO.IS?range=5d&interval=1d", None),
    ]
    headers = {"User-Agent": "Mozilla/5.0 (faz0-source-test; research)"}
    out = []
    for name, method, url, params in checks:
        rec = {"check": name, "url": url}
        t0 = time.time()
        try:
            r = requests.request(method, url, params=params, headers=headers, timeout=30)
            rec.update(status=r.status_code, bytes=len(r.content), seconds=round(time.time() - t0, 2),
                       content_type=r.headers.get("content-type", ""))
            if name == "borsa_istanbul_csv" and r.ok:
                rec.update(_summarize_bist_csv(r.content))
            if name == "isyatirim_malitablo" and r.ok:
                try:
                    rec["items"] = len(r.json().get("value") or [])
                except ValueError:
                    rec["items"] = "json_degil"
        except Exception as exc:  # noqa: BLE001 — her hatayı kaydetmek istiyoruz
            rec.update(status=None, error=f"{type(exc).__name__}: {exc}", seconds=round(time.time() - t0, 2))
        log(f"erişim {name}: {rec.get('status')} {rec.get('error', '')}")
        out.append(rec)
        pause()
    return out


def _summarize_bist_csv(content: bytes) -> dict:
    """Evren sorusu için: CSV'de kaç benzersiz hisse ve kaç XYLDZ bileşeni var."""
    text = content.decode("utf-8", errors="replace")
    rows = [line.split(";") for line in text.splitlines()]
    eq = [r for r in rows if len(r) >= 3 and r[0].strip().endswith(".E")]
    all_tickers = {r[0].strip() for r in eq}
    xyldz = {r[0].strip() for r in eq if r[2].strip() == "XYLDZ"}
    xusin = {r[0].strip() for r in eq if r[2].strip() == "XUTUM"}
    return {"csv_rows": len(rows), "csv_unique_E": len(all_tickers),
            "csv_XYLDZ": len(xyldz), "csv_XUTUM": len(xusin)}


# ---------------------------------------------------------------- İş Yatırım (isyatirimhisse)
def fetch_isyatirimhisse(ticker: str) -> tuple[str, pd.DataFrame, list[dict]]:
    """Yıl yıl çeker (her çağrı 4 çeyrek). Aile tespiti: XI_29 → UFRS_K (konsolide) → UFRS (solo).

    UFRS = konsolide OLMAYAN banka/sigorta tablosu, UFRS_K = konsolide (GARAN toplam
    varlığı ile doğrulandı, bkz. LEARNING.md). yfinance konsolideyi verdiği için önce K.
    """
    from isyatirimhisse import fetch_financials

    events = []
    for group_code, group_label in (("1", "XI_29"), ("3", "UFRS_K"), ("2", "UFRS")):
        frames = []
        for year in range(min(YEARS), 2027):
            # Paket zaman aşımını 10 sn'ye sabitlemiş, hatayı yalnızca print ediyor ve
            # zaman aşımını "veri yok" ile aynı hatayla bildiriyor. Bu yüzden boş dönen yılı
            # 3 kez deniyoruz (aralarda 10 sn); deneme sayısı kaydediliyor.
            for attempt in (1, 2, 3):
                try:
                    df = fetch_financials(symbols=ticker, start_year=year, end_year=year,
                                          financial_group=group_code)
                    frames.append(df)
                    events.append({"year": year, "group": group_label, "rows": len(df), "attempt": attempt})
                    break
                except Exception as exc:  # noqa: BLE001
                    events.append({"year": year, "group": group_label, "error": str(exc)[:200], "attempt": attempt})
                    time.sleep(10)
                finally:
                    pause()
            if year == min(YEARS) and not frames:
                break  # bu grupta hiç veri yok, diğer grubu dene
        if frames:
            merged = frames[0]
            for f in frames[1:]:
                merged = merged.merge(f.drop(columns=["SYMBOL"]), how="outer",
                                      on=["FINANCIAL_ITEM_CODE", "FINANCIAL_ITEM_NAME_TR", "FINANCIAL_ITEM_NAME_EN"])
            return group_label, merged, events
    return "", pd.DataFrame(), events


def classify_family(group: str, df: pd.DataFrame) -> str:
    if group == "XI_29":
        return "industrial"
    if group in ("UFRS", "UFRS_K"):
        names = df.set_index("FINANCIAL_ITEM_CODE")["FINANCIAL_ITEM_NAME_TR"]
        if "MEVDUAT" in str(names.get("2A", "")).upper():
            return "bank"
        return "insurance"
    return "unknown"


def isy_values(df: pd.DataFrame, family: str) -> list[dict]:
    recs = []
    codes = ISY_CODES.get(family, {})
    idx = df.set_index("FINANCIAL_ITEM_CODE")
    period_cols = [c for c in df.columns if "/" in str(c)]
    for item in ITEMS:
        item_codes = codes.get(item)
        for col in period_cols:
            y, m = (int(x) for x in col.split("/"))
            val = None
            note = ""
            if item_codes is None:
                note = "kalem_yok"
            else:
                parts = []
                for c in item_codes:
                    v = idx[col].get(c) if c in idx.index else None
                    if isinstance(v, pd.Series):
                        v = v.iloc[0]
                    parts.append(None if v is None or pd.isna(v) else float(v))
                if all(p is None for p in parts):
                    note = "bos"
                else:
                    val = sum(p for p in parts if p is not None)
            recs.append({"year": y, "month": m, "item": item, "value": val, "note": note})
    return recs


# ---------------------------------------------------------------- borsapy
def fetch_borsapy(ticker: str, family: str, isy_group: str) -> tuple[list[dict], list[dict]]:
    import borsapy as bp

    fg = isy_group if family in ("bank", "insurance") else None
    t = bp.Ticker(ticker)
    tables: dict[tuple[str, bool], pd.DataFrame] = {}
    events = []
    for stmt in ("balance_sheet", "income_stmt", "cashflow"):
        for quarterly in (False, True):
            if family in ("bank", "insurance") and stmt == "cashflow":
                continue
            fn = getattr(t, f"get_{stmt}")
            try:
                tables[(stmt, quarterly)] = fn(quarterly=quarterly, financial_group=fg, last_n=5)
                events.append({"stmt": stmt, "quarterly": quarterly, "cols": list(tables[(stmt, quarterly)].columns)})
            except Exception as exc:  # noqa: BLE001
                events.append({"stmt": stmt, "quarterly": quarterly, "error": f"{type(exc).__name__}: {exc}"[:200]})
            pause()

    recs = []
    rowmap = BPY_ROWS.get(family, {})
    for item in ITEMS:
        spec = rowmap.get(item)
        for quarterly in (False, True):
            df = tables.get((spec[0], quarterly)) if spec else None
            if df is None or df.empty:
                continue
            for col in df.columns:
                if quarterly:
                    y, q = str(col).split("Q")
                    y, m = int(y), int(q) * 3
                else:
                    y, m = int(col), 12
                vals = []
                dup = False
                for name in spec[1]:
                    hits = [i for i in df.index if str(i).strip() == name]
                    if len(hits) > 1:
                        dup = True
                    if item == "financial_debt" and family == "industrial":
                        # kısa + uzun vadeli — aynı ada sahip iki satır
                        sub = df.loc[[str(i).strip() == name for i in df.index], col]
                        vals.extend(pd.to_numeric(sub, errors="coerce").dropna().tolist())
                    elif hits:
                        v = df.loc[hits[0], col]
                        if isinstance(v, pd.Series):
                            v = v.iloc[0]
                        v = pd.to_numeric(v, errors="coerce")
                        if pd.notna(v):
                            vals.append(float(v))
                recs.append({"year": y, "month": m, "item": item,
                             "value": sum(vals) if vals else None,
                             "note": ("ayni_adli_satir" if dup else "") + ("" if vals else "bos")})
    return recs, events


# ---------------------------------------------------------------- yfinance
def fetch_yfinance(ticker: str) -> tuple[list[dict], dict]:
    import yfinance as yf

    t = yf.Ticker(f"{ticker}.IS")
    meta: dict = {}
    try:
        info = t.info
        meta = {k: info.get(k) for k in ("currency", "financialCurrency", "sharesOutstanding",
                                         "impliedSharesOutstanding", "sector", "industry")}
    except Exception as exc:  # noqa: BLE001
        meta = {"error": f"{type(exc).__name__}: {exc}"[:200]}
    pause()

    tables = {}
    for key, annual_attr, q_attr in (("balance", "balance_sheet", "quarterly_balance_sheet"),
                                     ("income", "income_stmt", "quarterly_income_stmt"),
                                     ("cashflow", "cashflow", "quarterly_cashflow")):
        for quarterly, attr in ((False, annual_attr), (True, q_attr)):
            try:
                tables[(key, quarterly)] = getattr(t, attr)
            except Exception as exc:  # noqa: BLE001
                meta[f"{attr}_error"] = str(exc)[:200]
                tables[(key, quarterly)] = pd.DataFrame()
            pause()

    recs = []
    for item in ITEMS:
        key, names = YF_ROWS[item]
        for quarterly in (False, True):
            df = tables.get((key, quarterly))
            if df is None or df.empty:
                continue
            row = next((n for n in names if n in df.index), None)
            for col in df.columns:
                ts = pd.Timestamp(col)
                v = df.loc[row, col] if row else None
                v = None if v is None or pd.isna(v) else float(v)
                recs.append({"year": ts.year, "month": ts.month, "item": item, "value": v,
                             "period_type": "Q" if quarterly else "A",
                             "note": f"row={row}" if row else "satir_yok"})
    return recs, meta


# ---------------------------------------------------------------- ana akış
def run(tickers: list[str], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    env = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": socket.gethostname(), "platform": platform.platform(), "python": sys.version.split()[0],
        "github_actions": bool(__import__("os").environ.get("GITHUB_ACTIONS")),
    }
    try:
        env["public_ip"] = requests.get("https://api.ipify.org", timeout=10).text
    except Exception:  # noqa: BLE001
        env["public_ip"] = None
    log(f"ortam: {env}")

    conn = connectivity_check()
    pd.DataFrame(conn).to_csv(out / "connectivity.csv", index=False)

    rows: list[dict] = []
    meta: dict[str, dict] = {}
    for i, tk in enumerate(tickers, 1):
        log(f"({i}/{len(tickers)}) {tk}")
        m: dict = {}
        try:
            group, df, ev = fetch_isyatirimhisse(tk)
            family = classify_family(group, df) if not df.empty else "unknown"
            m.update(isy_group=group, family=family, isy_events=ev)
            if not df.empty:
                for r in isy_values(df, family):
                    rows.append({"ticker": tk, "source": "isyatirimhisse", "cumulative": True, **r})
        except Exception:  # noqa: BLE001
            m["isy_error"] = traceback.format_exc(limit=2)
            family = "unknown"
        try:
            recs, ev = fetch_borsapy(tk, family, m.get("isy_group", ""))
            m["bpy_events"] = ev
            for r in recs:
                rows.append({"ticker": tk, "source": "borsapy", "cumulative": True, **r})
        except Exception:  # noqa: BLE001
            m["bpy_error"] = traceback.format_exc(limit=2)
        try:
            recs, ym = fetch_yfinance(tk)
            m["yf_meta"] = ym
            for r in recs:
                rows.append({"ticker": tk, "source": "yfinance", "cumulative": False, **r})
        except Exception:  # noqa: BLE001
            m["yf_error"] = traceback.format_exc(limit=2)
        meta[tk] = m

    raw = pd.DataFrame(rows)
    raw.to_csv(out / "raw_values.csv", index=False)
    (out / "meta.json").write_text(json.dumps({"env": env, "tickers": meta}, ensure_ascii=False, indent=1,
                                              default=str), encoding="utf-8")
    summarize(raw, meta, out)


def _discrete_quarters(isy: pd.DataFrame) -> pd.DataFrame:
    """İş Yatırım kümülatif çeyreklerini tekil çeyreğe çevirir (yalnız akım kalemleri)."""
    isy = isy.copy()
    isy["q_value"] = isy["value"]
    for (tk, item, y), g in isy.groupby(["ticker", "item", "year"]):
        if item not in FLOW_ITEMS:
            continue
        g = g.set_index("month")["value"]
        for mth in (6, 9, 12):
            prev = g.get(mth - 3)
            cur = g.get(mth)
            sel = (isy.ticker == tk) & (isy.item == item) & (isy.year == y) & (isy.month == mth)
            isy.loc[sel, "q_value"] = (cur - prev) if (cur is not None and prev is not None
                                                      and pd.notna(cur) and pd.notna(prev)) else None
    return isy


def summarize(raw: pd.DataFrame, meta: dict, out: Path) -> None:
    targets_q = set(QUARTERS)
    targets_a = {(y, 12) for y in YEARS}

    isy = raw[raw.source == "isyatirimhisse"]
    bpy = raw[raw.source == "borsapy"]
    yfq = raw[(raw.source == "yfinance") & (raw.period_type == "Q")]
    yfa = raw[(raw.source == "yfinance") & (raw.period_type == "A")]

    # 1) Eksik oranı: hedef hücre (ticker × item × dönem) başına değer var mı
    cov = []
    tickers = sorted(meta)
    fam_of = {tk: ("finansal" if meta[tk].get("family") in ("bank", "insurance") else "sanayi") for tk in tickers}
    for src, df_q, df_a in (("isyatirimhisse", isy, isy), ("borsapy", bpy, bpy), ("yfinance", yfq, yfa)):
        for item in ITEMS:
            for ptype, targets, df in (("ceyrek", targets_q, df_q), ("yillik", targets_a, df_a)):
                have = df[(df.item == item) & df.value.notna()]
                have = {(r.ticker, r.year, r.month) for r in have.itertuples()}
                for fam in ("sanayi", "finansal"):
                    tks = [tk for tk in tickers if fam_of[tk] == fam]
                    total = len(tks) * len(targets)
                    got = sum(1 for tk in tks for (y, m) in targets if (tk, y, m) in have)
                    cov.append({"aile": fam, "kaynak": src, "kalem": item, "donem": ptype, "dolu": got,
                                "hedef": total, "eksik_oran": round(1 - got / total, 3) if total else None})
    pd.DataFrame(cov).to_csv(out / "coverage.csv", index=False)

    # 2) Kaynaklar arası fark
    isy_d = _discrete_quarters(isy) if not isy.empty else isy
    key = ["ticker", "item", "year", "month"]
    diffs = []

    def cmp(a: pd.DataFrame, b: pd.DataFrame, a_col: str, label: str, targets: set) -> None:
        m = a.merge(b, on=key, suffixes=("_a", "_b"))
        for r in m.itertuples():
            if (r.year, r.month) not in targets:
                continue
            va, vb = getattr(r, a_col), r.value
            if va is None or vb is None or pd.isna(va) or pd.isna(vb):
                continue
            rel = abs(va - vb) / abs(vb) if vb else (0.0 if va == 0 else None)
            diffs.append({"karsilastirma": label, "ticker": r.ticker, "kalem": r.item,
                          "donem": f"{r.year}/{r.month}", "a": va, "b": vb,
                          "fark_oran": None if rel is None else round(rel, 4)})

    isy_a = isy_d.rename(columns={"value": "value_isy"})
    cmp(isy_a.assign(value_a=isy_a.value_isy)[key + ["value_a"]], bpy[key + ["value"]],
        "value_a", "isyatirimhisse_vs_borsapy", targets_q | targets_a)
    # yıllık: Aralık kümülatifi = yıllık
    cmp(isy_a.assign(value_a=isy_a.value_isy)[key + ["value_a"]], yfa[key + ["value"]],
        "value_a", "isy_vs_yfinance_yillik", targets_a)
    # çeyreklik: akım kalemlerinde tekil çeyrek, stokta dönem sonu
    isy_q = isy_d.assign(value_a=isy_d.apply(lambda r: r.q_value if r["item"] in FLOW_ITEMS else r.value, axis=1))
    cmp(isy_q[key + ["value_a"]], yfq[key + ["value"]], "value_a", "isy_vs_yfinance_ceyrek", targets_q)
    dd = pd.DataFrame(diffs).drop_duplicates()
    dd.to_csv(out / "diffs.csv", index=False)

    # 3) Hisse bazında özet: para birimi, en güncel dönem, aile
    per = []
    for tk in tickers:
        m = meta[tk]
        ym = m.get("yf_meta", {}) or {}

        def latest(df: pd.DataFrame) -> str:
            d = df[(df.ticker == tk) & df.value.notna() & (df.item == "total_assets")]
            if d.empty:
                return "-"
            y, mth = max(zip(d.year, d.month))
            return f"{y}/{mth}"
        per.append({"ticker": tk, "aile": m.get("family"), "isy_grup": m.get("isy_group"),
                    "yf_currency": ym.get("currency"), "yf_financialCurrency": ym.get("financialCurrency"),
                    "yf_sharesOutstanding": ym.get("sharesOutstanding"),
                    "son_donem_isy": latest(isy), "son_donem_borsapy": latest(bpy),
                    "son_donem_yf_ceyrek": latest(yfq), "son_donem_yf_yillik": latest(yfa)})
    pd.DataFrame(per).to_csv(out / "per_ticker.csv", index=False)

    # 4) Okunabilir özet
    covdf = pd.DataFrame(cov)
    piv = covdf.pivot_table(index=["aile", "kalem", "donem"], columns="kaynak", values="eksik_oran").reset_index()
    lines = [f"# Faz 0 kaynak testi — {datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
             "## Erişim", "", pd.read_csv(out / "connectivity.csv").to_markdown(index=False), "",
             "## Eksik oranı (0 = tam, 1 = hiç yok)", "", piv.to_markdown(index=False), "",
             "## Hisse bazında", "", pd.DataFrame(per).to_markdown(index=False), ""]
    if not dd.empty:
        dd["fark_gt_2pct"] = dd.fark_oran > 0.02
        g = dd.groupby(["karsilastirma", "kalem"]).agg(
            n=("fark_oran", "size"), medyan_fark=("fark_oran", "median"),
            fark_gt_2pct=("fark_gt_2pct", "sum")).reset_index()
        lines += ["## Kaynaklar arası fark (göreli)", "", g.to_markdown(index=False), ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    log(f"bitti → {out}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/faz0/local")
    ap.add_argument("--tickers", default=",".join(TICKERS))
    ap.add_argument("--summarize-only", action="store_true", help="raw_values.csv + meta.json'dan özet üret")
    args = ap.parse_args()
    out = Path(args.out)
    if args.summarize_only:
        raw = pd.read_csv(out / "raw_values.csv")
        meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))["tickers"]
        summarize(raw, meta, out)
        return
    run([t.strip().upper() for t in args.tickers.split(",") if t.strip()], out)


if __name__ == "__main__":
    main()
