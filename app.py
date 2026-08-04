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

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import connection as db
from providers import news_provider

st.set_page_config(page_title="BIST Alpha Score", page_icon="📊", layout="wide")

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
    company_name = news_provider.get_company_name(ticker)
    return {
        "yfinance": news_provider.fetch_yfinance_news(ticker),
        "kap": news_provider.fetch_kap_disclosures(ticker),
        "google": news_provider.fetch_google_news_rss(company_name),
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
    """Her ticker için EN GÜNCEL calculation_date'teki pillar_scores satırlarını çeker."""
    engine = db.get_engine()
    query = text(
        """
        SELECT ps.ticker, ps.calculation_date, ps.pillar_name, ps.pillar_score,
               ps.pillar_weight, ps.total_score, ps.momentum_flag, ps.notes
        FROM pillar_scores ps
        INNER JOIN (
            SELECT ticker, MAX(calculation_date) AS max_date
            FROM pillar_scores
            GROUP BY ticker
        ) latest ON ps.ticker = latest.ticker AND ps.calculation_date = latest.max_date
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def build_overview_table(df: pd.DataFrame) -> pd.DataFrame:
    """Uzun formattaki (bir satır = bir pillar) veriyi geniş formata (bir satır = bir ticker) çevirir."""
    pivot = df.pivot_table(index="ticker", columns="pillar_name", values="pillar_score", aggfunc="first")
    pivot = pivot.reindex(columns=_PILLAR_ORDER)
    summary = df.groupby("ticker").agg(
        total_score=("total_score", "first"),
        momentum_flag=("momentum_flag", "first"),
        calculation_date=("calculation_date", "first"),
    )
    result = summary.join(pivot).reset_index()
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

    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Ticker ara", placeholder="örn. TUPRS")
    with col2:
        only_weak_momentum = st.checkbox("Sadece momentum uyarılı", value=False)

    filtered = overview.copy()
    if search:
        filtered = filtered[filtered["ticker"].str.contains(search.upper(), na=False)]
    if only_weak_momentum:
        filtered = filtered[filtered["momentum_flag"] == True]  # noqa: E712

    display_df = filtered.rename(
        columns={
            "ticker": "Ticker",
            "total_score": "Toplam Skor",
            "momentum_flag": "Momentum Zayıf",
            "calculation_date": "Hesaplama Tarihi",
            "profitability": "Kârlılık",
            "safety": "Sağlamlık",
            "valuation": "Değerleme",
            "size": "Büyüklük",
        }
    )

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

        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Skor", f"{row_summary['total_score']:.0f}/100" if pd.notna(row_summary["total_score"]) else "veri yok")
        m2.metric("Hesaplama Tarihi", str(row_summary["calculation_date"]))
        m3.metric("Momentum", "⚠️ Zayıf" if row_summary["momentum_flag"] else "Normal")

        chart_data = pd.DataFrame(
            {
                "Pillar": [_PILLAR_LABELS[p] for p in _PILLAR_ORDER if p in ticker_rows.index],
                "Skor": [ticker_rows.loc[p, "pillar_score"] for p in _PILLAR_ORDER if p in ticker_rows.index],
                "Renk": [_PILLAR_COLORS[p] for p in _PILLAR_ORDER if p in ticker_rows.index],
            }
        )
        st.bar_chart(chart_data, x="Pillar", y="Skor", color="Renk", horizontal=True)

        st.markdown("**Pillar detay notları:**")
        for p in _PILLAR_ORDER:
            if p in ticker_rows.index:
                score = ticker_rows.loc[p, "pillar_score"]
                score_text = f"{score:.0f}/100" if pd.notna(score) else "veri yok"
                with st.expander(f"{_PILLAR_LABELS[p]} — {score_text}"):
                    st.write(ticker_rows.loc[p, "notes"])

        st.divider()
        render_news_section(selected)


if __name__ == "__main__":
    main()
