"""BIST Alpha Score — web arayüzü.

Skorlar için uygulama katmanı sadece veritabanını okur (canlı yfinance/KAP
API'lerine bağlanmaz) — proje mimarisinin "Data Provider -> Normalizer ->
Database -> Score Engine -> [bu katman]" zincirindeki son halka. Skorları
güncellemek için scripts/calculate_alpha_score.py'yi ayrıca çalıştırmanız
gerekir.

İSTİSNA: Hisse detayı panelindeki "Güncel Haberler / Bildirimler" bölümü
bilinçli olarak bu kuralın dışında — skorlama pipeline'ının parçası değil,
veritabanına hiçbir şey yazmıyor, sadece tıklandığında anlık (canlı) olarak
providers/news_provider.py üzerinden üç kaynağı (yfinance, KAP, Google News)
çekip gösteriyor.

Çalıştırma: streamlit run app.py
"""
from __future__ import annotations

import subprocess

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import connection as db
from providers import news_provider

st.set_page_config(page_title="BIST Alpha Score", page_icon="📊", layout="wide")


@st.cache_resource
def _ensure_playwright_browser() -> None:
    """KAP bildirimleri Playwright/Chromium gerektiriyor (bkz. news_provider.py).

    `pip install playwright` sadece kütüphaneyi kurar, tarayıcı BİNARİSİNİ
    kurmaz — bu normalde ayrı bir `playwright install chromium` komutuyla
    yapılır. Streamlit Community Cloud'da bunu deploy sırasında otomatik
    çalıştıracak bir kanca yok (packages.txt sadece apt paketleri kabul
    ediyor), o yüzden uygulama kendi başlangıcında (süreç başına BİR KEZ,
    st.cache_resource sayesinde) tarayıcının kurulu olduğundan emin oluyor.
    Zaten kuruluysa `playwright install` hızlıca no-op döner.
    """
    try:
        subprocess.run(["playwright", "install", "chromium"], check=False, timeout=180)
    except Exception:
        pass  # KAP bölümü olmadan da uygulamanın geri kalanı çalışmaya devam etsin


_ensure_playwright_browser()

# scoring/pillars.py::PILLAR_WEIGHTS ile aynı sabit sıra — kategorik renkler
# bu sıraya göre atanıyor, veriye göre değil (dataviz ilkesi: sabit sıra).
_PILLAR_ORDER = ["profitability", "safety", "valuation", "size"]
_PILLAR_LABELS = {
    "profitability": "Kârlılık",
    "safety": "Finansal Sağlamlık",
    "valuation": "Değerleme",
    "size": "Büyüklük",
}
# references/palette.md — ilk 4 slot, adjacent-pair olarak doğrulanmış (sabit sıra).
_PILLAR_COLORS = {
    "profitability": "#2a78d6",  # blue
    "safety": "#1baf7a",         # aqua
    "valuation": "#eb6834",      # orange
    "size": "#eda100",           # yellow
}


@st.cache_data(ttl=1800)  # 30 dakika — KAP taraması (Playwright) yavaş, gereksiz tekrar taramayı önle
def load_news(ticker: str) -> dict[str, list[dict]]:
    """Bir ticker için üç kaynaktan da haberleri/bildirimleri çeker.

    Kaynaklardan biri boş/hatalı dönerse news_provider zaten sessizce boş
    liste döndürüyor (bkz. o modüldeki hata yönetimi) — burada ek try/except
    gerekmiyor, çağıran taraf (render_news_section) boş listeyi "bulunamadı"
    mesajına çevirir.
    """
    return {
        "yfinance": news_provider.fetch_yfinance_news(ticker),
        "kap": news_provider.fetch_kap_disclosures(ticker),
        "google": news_provider.fetch_google_news_rss(ticker),
    }


def render_news_list(items: list[dict], empty_message: str) -> None:
    if not items:
        st.caption(empty_message)
        return
    for item in items:
        date_text = item["date"].strftime("%d.%m.%Y %H:%M") if item["date"] else "tarih yok"
        title = item["title"]
        if item.get("url"):
            st.markdown(
                f"<a href='{item['url']}' target='_blank'>{title}</a>"
                f"<br><span style='color:gray;font-size:0.85em'>{item['source']} — {date_text}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"{title}  \n<span style='color:gray;font-size:0.85em'>{item['source']} — {date_text}</span>", unsafe_allow_html=True)
        st.markdown("---")


def render_news_section(ticker: str) -> None:
    st.subheader("📰 Güncel Haberler / Bildirimler")
    with st.spinner("Haberler yükleniyor..."):
        news = load_news(ticker)

    n1, n2, n3 = st.columns(3)
    with n1:
        st.markdown("**Yahoo Finance**")
        render_news_list(news["yfinance"], "Bu kaynakta güncel haber bulunamadı.")
    with n2:
        st.markdown("**KAP Bildirimleri**")
        render_news_list(news["kap"], "Bu kaynakta güncel bildirim bulunamadı.")
    with n3:
        st.markdown("**Google News**")
        render_news_list(news["google"], "Bu kaynakta güncel haber bulunamadı.")


@st.cache_data(ttl=300)
def load_latest_pillar_scores() -> pd.DataFrame:
    """Her ticker için EN GÜNCEL run'ın (created_at) pillar_scores satırlarını çeker.

    calculation_date GÜN hassasiyetinde (DATE) olduğu için değil, created_at
    (TIMESTAMPTZ) ile seçiyoruz — aynı ticker aynı gün içinde birden fazla
    kez çalıştırılırsa calculation_date'e göre gruplamak o günün TÜM
    run'larının satırlarını (tekrar tekrar) döndürürdü. bkz.
    db.save_pillar_scores'taki created_at açıklaması.
    """
    engine = db.get_engine()
    query = text(
        """
        SELECT ps.ticker, ps.calculation_date, ps.pillar_name, ps.pillar_score,
               ps.pillar_weight, ps.total_score, ps.momentum_flag, ps.notes, ps.period_date,
               ps.profitability_signal
        FROM pillar_scores ps
        INNER JOIN (
            SELECT ticker, MAX(created_at) AS max_created_at
            FROM pillar_scores
            GROUP BY ticker
        ) latest ON ps.ticker = latest.ticker AND ps.created_at = latest.max_created_at
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def build_overview_table(df: pd.DataFrame) -> pd.DataFrame:
    """Uzun formattaki (bir satır = bir pillar) veriyi geniş formata (bir satır = bir ticker) çevirir."""
    pivot = df.pivot_table(index="ticker", columns="pillar_name", values="pillar_score", aggfunc="first")
    pivot = pivot.reindex(columns=_PILLAR_ORDER)
    # period_date sadece Kârlılık/Sağlamlık satırlarında dolu (Değerleme/Büyüklük
    # anlık piyasa verisine dayandığı için NULL) — dropna().first() ile
    # ticker başına dolu olan tek bir "finansal dönem" değeri çıkarıyoruz.
    summary = df.groupby("ticker").agg(
        total_score=("total_score", "first"),
        momentum_flag=("momentum_flag", "first"),
        calculation_date=("calculation_date", "first"),
        financial_period_date=("period_date", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
        profitability_signal=("profitability_signal", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
    )
    result = summary.join(pivot).reset_index()
    # profitability_ttm PILLAR_WEIGHTS'te yok, pivot'ta ayrı bir sütun olarak
    # geliyor — genel tabloda ayrıca göstermiyoruz (ana skor kartında zaten
    # sadece 4 ağırlıklı pillar var), ama sinyal filtresi için elde tutuluyor.
    result["is_recovery_signal"] = result["profitability_signal"].fillna("").str.contains("TOPARLANMA")
    result = result.sort_values("total_score", ascending=False, na_position="last")
    return result


def main() -> None:
    st.title("📊 BIST Alpha Score")
    st.caption(
        "4 pillar (Kârlılık %35, Finansal Sağlamlık %30, Değerleme %20, Büyüklük %10) "
        "+ momentum filtresi. Yatırım tavsiyesi değildir, sadece bilgilendirme amaçlıdır."
    )

    try:
        df = load_latest_pillar_scores()
    except Exception as exc:
        st.error(f"Veritabanına bağlanılamadı: {exc}")
        st.stop()

    if df.empty:
        st.warning(
            "pillar_scores tablosunda hiç veri yok. Önce "
            "`python scripts/calculate_alpha_score.py TICKER1 TICKER2 ...` çalıştırın."
        )
        st.stop()

    overview = build_overview_table(df)

    st.subheader(f"Genel Bakış ({len(overview)} hisse)")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search = st.text_input("Ticker ara", placeholder="örn. TUPRS")
    with col2:
        only_weak_momentum = st.checkbox("Sadece momentum uyarılı", value=False)
    with col3:
        only_recovery = st.checkbox(
            "🔼 Sadece toparlanma sinyali",
            value=False,
            help="Son 12 aylık (TTM) Kârlılık skoru, yıllık skordan belirgin "
            "(±15 puan eşiği) yüksek olan hisseler — 270 şirket arasından "
            "erken toparlanma sinyali verenleri hızlıca süzmek için.",
        )

    filtered = overview.copy()
    if search:
        filtered = filtered[filtered["ticker"].str.contains(search.upper(), na=False)]
    if only_weak_momentum:
        filtered = filtered[filtered["momentum_flag"] == True]  # noqa: E712
    if only_recovery:
        filtered = filtered[filtered["is_recovery_signal"]]

    display_df = filtered.rename(
        columns={
            "ticker": "Ticker",
            "total_score": "Toplam Skor",
            "momentum_flag": "Momentum Zayıf",
            "calculation_date": "Hesaplama Tarihi",
            "financial_period_date": "Finansal Dönem",
            "profitability": "Kârlılık",
            "safety": "Sağlamlık",
            "valuation": "Değerleme",
            "size": "Büyüklük",
            "profitability_signal": "Kârlılık Sinyali",
        }
    )
    display_df = display_df.drop(columns=["is_recovery_signal", "profitability_ttm"], errors="ignore")

    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Toplam Skor": st.column_config.ProgressColumn(
                "Toplam Skor", min_value=0, max_value=100, format="%.0f"
            ),
            "Kârlılık": st.column_config.ProgressColumn("Kârlılık", min_value=0, max_value=100, format="%.0f"),
            "Sağlamlık": st.column_config.ProgressColumn("Sağlamlık", min_value=0, max_value=100, format="%.0f"),
            "Değerleme": st.column_config.ProgressColumn("Değerleme", min_value=0, max_value=100, format="%.0f"),
            "Büyüklük": st.column_config.ProgressColumn("Büyüklük", min_value=0, max_value=100, format="%.0f"),
            "Momentum Zayıf": st.column_config.CheckboxColumn("⚠️ Momentum Zayıf"),
        },
    )

    st.divider()
    st.subheader("Hisse Detayı")
    ticker_options = sorted(overview["ticker"].tolist())
    selected = st.selectbox("Bir ticker seçin", ticker_options)

    if selected:
        ticker_rows = df[df["ticker"] == selected].set_index("pillar_name")
        row_summary = overview[overview["ticker"] == selected].iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Skor", f"{row_summary['total_score']:.0f}/100" if pd.notna(row_summary["total_score"]) else "veri yok")
        m2.metric("Hesaplama Tarihi", str(row_summary["calculation_date"]))
        m3.metric("Momentum", "⚠️ Zayıf" if row_summary["momentum_flag"] else "Normal")
        m4.metric(
            "Finansal Dönem",
            str(row_summary["financial_period_date"]) if pd.notna(row_summary["financial_period_date"]) else "veri yok",
            help="Kârlılık ve Finansal Sağlamlık pillar'larının dayandığı mali dönem sonu. "
            "Değerleme ve Büyüklük anlık piyasa verisine dayanır, bu tarihe bağlı değildir.",
        )

        chart_data = pd.DataFrame(
            {
                "Pillar": [_PILLAR_LABELS[p] for p in _PILLAR_ORDER if p in ticker_rows.index],
                "Skor": [ticker_rows.loc[p, "pillar_score"] for p in _PILLAR_ORDER if p in ticker_rows.index],
                "Renk": [_PILLAR_COLORS[p] for p in _PILLAR_ORDER if p in ticker_rows.index],
            }
        )
        st.bar_chart(chart_data, x="Pillar", y="Skor", color="Renk", horizontal=True)
        st.caption(
            "Bu grafikteki Kârlılık YILLIK skordur (toplam skora giren tek Kârlılık "
            "değeri) — aşağıda TTM (son 12 ay) ile karşılaştırması ayrıca var."
        )

        st.markdown("**Kârlılık: Yıllık vs Son 12 Ay (TTM)**")
        annual_score = ticker_rows.loc["profitability", "pillar_score"] if "profitability" in ticker_rows.index else None
        ttm_score = (
            ticker_rows.loc["profitability_ttm", "pillar_score"] if "profitability_ttm" in ticker_rows.index else None
        )
        p1, p2 = st.columns(2)
        p1.metric("Kârlılık (Yıllık)", f"{annual_score:.0f}/100" if pd.notna(annual_score) else "veri yok")
        p2.metric("Kârlılık (Son 12 Ay)", f"{ttm_score:.0f}/100" if pd.notna(ttm_score) else "veri yok")

        signal_message = row_summary.get("profitability_signal")
        if pd.notna(signal_message):
            if "TOPARLANMA" in signal_message:
                st.success(signal_message)
            elif "BOZULMA" in signal_message:
                st.warning(signal_message)
            else:
                st.info(signal_message)

        st.markdown("**Pillar detay notları:**")
        for p in _PILLAR_ORDER:
            if p in ticker_rows.index:
                score = ticker_rows.loc[p, "pillar_score"]
                score_text = f"{score:.0f}/100" if pd.notna(score) else "veri yok"
                with st.expander(f"{_PILLAR_LABELS[p]} — {score_text}"):
                    st.write(ticker_rows.loc[p, "notes"])
        if "profitability_ttm" in ticker_rows.index:
            score_text = f"{ttm_score:.0f}/100" if pd.notna(ttm_score) else "veri yok"
            with st.expander(f"Kârlılık (Son 12 Ay / TTM) — {score_text}"):
                st.write(ticker_rows.loc["profitability_ttm", "notes"])

        st.divider()
        render_news_section(selected)


if __name__ == "__main__":
    main()
