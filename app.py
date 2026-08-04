"""BIST Alpha Score — web arayüzü.

Uygulama katmanı sadece veritabanını okur (canlı yfinance/KAP API'lerine
bağlanmaz) — proje mimarisinin "Data Provider -> Normalizer -> Database ->
Score Engine -> [bu katman]" zincirindeki son halka. Skorları güncellemek
için scripts/calculate_alpha_score.py'yi ayrıca çalıştırmanız gerekir.

Çalıştırma: streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import connection as db

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


if __name__ == "__main__":
    main()
