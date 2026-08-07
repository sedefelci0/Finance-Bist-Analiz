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

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import connection as db
from providers import news_provider
from scoring import ai_commentary
from scoring.fscore_criteria_definitions import CATEGORIES, CRITERIA_INFO, build_why_explanation

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

# "Pillar detay notları" altındaki "ℹ️ Bu skorlar nasıl hesaplanıyor?" için —
# scoring/pillars.py + scoring/altman_z.py + scoring/piotroski.py'deki
# formüllerin kullanıcıya yönelik, sade Türkçe özeti. Hesaplama mantığı
# değişirse (eşikler, ağırlıklar) burası da güncellenmeli.
_METHODOLOGY_EXPLAINER = """
Her pillar, birkaç alt-oranın **0-100'e çevrilip ortalanmasıyla** hesaplanıyor.
Kârlılık ve Finansal Sağlamlık **mutlak eşiklere** göre; Değerleme ve Büyüklük
ise **göreceli** (peer grubuna göre yüzdelik dilim / percentile) puanlanıyor.

**Kârlılık** — 4 oranın ortalaması:

| Oran | Formül | 0 puan eşiği | 100 puan eşiği |
|---|---|---|---|
| ROE | Net Kâr ÷ Özkaynak | %0 | %25 |
| ROIC | EBIT×(1-vergi oranı) ÷ Yatırılan Sermaye | %0 | %20 |
| Brüt marj | Brüt Kâr ÷ Hasılat | %0 | %40 |
| Faaliyet marjı | EBIT ÷ Hasılat | %0 | %25 |

*(Kârlılık (Son 12 Ay / TTM) aynı 4 formülü kullanır, sadece girdiler
yıllık kapanmış tam mali yıl yerine kayan son 12 aya dayanır — normalde
yfinance'in son 4 çeyreğinin toplamı, ama yfinance'in çeyreklik verisi
gecikmişse (KAP'ta daha yeni bir açıklama varsa) o taze veriyle
"köprülenip" güncellenir; hangisi kullanıldığı pillar notlarında görünür.)*

**Finansal Sağlamlık** — 4 sinyalin ağırlıklı ortalaması:
- **F-Score + Z-Score bileşik (%50)**: F-Score, Piotroski'nin 9 kriterlik testi
  (kâr pozitif mi, nakit akışı kârdan büyük mü, borç azalıyor mu, vb. — kaç
  kriter sağlandı). Z-Score, Altman'ın iflas riski modeli (Z>2.99 = "güvenli
  bölge", <1.81 = "sıkıntılı bölge"). İkisi ayrı ayrı ağırlıklandırılmıyor,
  normalize edilip ortalanıyor.
- **Kaldıraç disiplini (%25)**: uzun vadeli borç/aktif oranı geçen yıla göre
  azalmış mı.
- **Cari oran (%25)**: dönen varlıklar ÷ kısa vadeli borç (likidite).

**Değerleme** — PE, PEG, EV/EBITDA, P/B çarpanlarının **aynı sektördeki**
şirketlere göre yüzdelik dilimi. Düşük çarpan (ucuz) = yüksek puan. Veri
eksikse ("yok") o çarpan ortalamaya katılmaz, notlarda "eksik: ..." diye
belirtilir.

**Büyüklük** — piyasa değeri (KÜÇÜK=yüksek puan, akademik "küçük şirket
primi" mantığıyla) ve beta'nın (düşük volatilite=yüksek puan) **tüm BIST
evrenine** göre yüzdelik dilimi.

Eşikler ve ağırlıklar kodda sabit tanımlı, tartışmaya açık — özellikle
Türkiye'deki enflasyon muhasebesi nominal rakamları şişirebildiği için
ileride kalibre edilmeleri gerekebilir.
"""


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
               ps.profitability_signal, ps.f_score_detail
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


# --- F-Score "şeffaf karar destek sistemi" bölümü ------------------------
# Sadece pillar_name = "safety" satırının notes'unun ALTINA eklenen UI —
# hesaplama mantığına dokunmuyor, scoring/pillars.py::calculate_safety_pillar'ın
# döndürdüğü f_score_detail'ı (bkz. db.save_pillar_scores) görselleştiriyor.

_RAW_METRIC_LABELS = {
    "net_income": "Net Kâr",
    "operating_cash_flow": "Faaliyet Nakit Akışı",
    "total_assets": "Toplam Varlıklar",
    "long_term_debt": "Uzun Vadeli Borç",
    "current_assets": "Dönen Varlıklar",
    "current_liabilities": "Kısa Vadeli Yükümlülükler",
    "shares_outstanding": "Hisse Sayısı",
    "gross_profit": "Brüt Kâr",
    "revenue": "Hasılat",
}


def _extract_f_score_detail(value) -> dict | None:
    """pillar_scores.f_score_detail (JSONB) -> dict, ya da None (kayıt yok/eski tarama)."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    return value if isinstance(value, dict) else None


def _fmt_by_kind(fmt: str | None, value) -> str:
    if value is None:
        return "veri yok"
    if fmt == "percent":
        return f"{value:.2%}"
    if fmt == "currency":
        return f"{value:,.0f} TL"
    if fmt == "count":
        return f"{value:,.0f}"
    return f"{value:.2f}"  # ratio ve tanımsız format


@st.cache_data(ttl=86400, show_spinner=False)
def _get_ai_commentary(ticker: str, f_score_detail: dict) -> str:
    """AI yorumunu (varsa) üretir, başarısız olursa şablon fallback'e düşer.

    24 saat cache'leniyor — her sayfa yenilemesinde yeniden LLM çağrısı
    yapılmasını (maliyet + gecikme) önlemek için; ticker + f_score_detail
    değiştiğinde (yeni tarama) cache anahtarı da değişir.
    """
    text_ = ai_commentary.generate_ai_commentary(f_score_detail, ticker)
    if text_:
        return text_
    return ai_commentary.generate_fallback_commentary(f_score_detail, ticker)


def render_fscore_transparency(ticker: str, detail: dict) -> None:
    criteria = detail.get("criteria", [])
    if not criteria:
        st.caption("Kriter kırılımı boş.")
        return

    total = detail.get("total_score", 0)
    calculated = detail.get("calculated_count", 0)
    st.markdown("#### F-Score — Kriter Kırılımı")
    st.caption(
        f"{calculated} kriterden {total} tanesi sağlandı. Bu, Finansal Sağlamlık "
        "pillar'ının SADECE bir bileşeni (F-Score+Z-Score bileşik %50) — üstteki "
        "pillar skoru bunun tek başına aynısı değil."
    )

    # 1) Kriter kırılım tablosu
    rows = []
    for c in criteria:
        info = CRITERIA_INFO.get(c["name"], {})
        if c["score"] is None:
            verdict = "❔ veri yok"
        elif c["score"] == 1:
            verdict = "✅ sağlandı"
        else:
            verdict = "❌ sağlanmadı"
        desc = info.get("description", "")
        rows.append(
            {
                "Kriter": info.get("label", c["name"]),
                "Sonuç": verdict,
                "Açıklama": (desc[:110] + "…") if len(desc) > 110 else desc,
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # 2) Kategori kartları (klasik Piotroski 3 grubu)
    st.markdown("**Kategori Bazında Özet**")
    cat_summary: dict[str, list[int]] = {key: [0, 0] for key in CATEGORIES}
    for c in criteria:
        cat = CRITERIA_INFO.get(c["name"], {}).get("category")
        if cat is None or c["score"] is None:
            continue
        cat_summary[cat][1] += 1
        if c["score"] == 1:
            cat_summary[cat][0] += 1
    cat_cols = st.columns(3)
    for col, (key, info) in zip(cat_cols, sorted(CATEGORIES.items(), key=lambda kv: kv[1]["order"])):
        passed, cnt = cat_summary[key]
        col.metric(info["label"], f"{passed}/{cnt}" if cnt else "veri yok")

    # 3) Donut grafik — sağlandı (yeşil) / sağlanmadı (kırmızı) / veri yok (nötr)
    # Renkler dataviz palette'inin sabit status renkleri: good=#0ca30c, critical=#d03b3b.
    passed_n = sum(1 for c in criteria if c["score"] == 1)
    failed_n = sum(1 for c in criteria if c["score"] == 0)
    na_n = sum(1 for c in criteria if c["score"] is None)
    donut_rows = [
        {"Durum": "✅ Sağlandı", "Sayı": passed_n, "Renk": "#0ca30c"},
        {"Durum": "❌ Sağlanmadı", "Sayı": failed_n, "Renk": "#d03b3b"},
    ]
    if na_n:
        donut_rows.append({"Durum": "❔ Veri Yok", "Sayı": na_n, "Renk": "#898781"})
    donut_data = pd.DataFrame([r for r in donut_rows if r["Sayı"] > 0])
    if not donut_data.empty:
        donut_chart = (
            alt.Chart(donut_data)
            .mark_arc(innerRadius=60)
            .encode(
                theta=alt.Theta("Sayı:Q"),
                color=alt.Color(
                    "Durum:N",
                    scale=alt.Scale(domain=donut_data["Durum"].tolist(), range=donut_data["Renk"].tolist()),
                    legend=alt.Legend(title=None),
                ),
                tooltip=["Durum", "Sayı"],
            )
            .properties(height=220)
        )
        st.altair_chart(donut_chart, use_container_width=True)

    # 4) Mini karşılaştırma — önceki dönem vs bu dönem (sayısal kriterler)
    st.markdown("**Önceki Dönem vs Bu Dönem**")
    compare_rows = []
    for c in criteria:
        d = c.get("detail") or {}
        if d.get("kind") != "compare_periods":
            continue
        prev_v, cur_v = d.get("prev"), d.get("cur")
        if prev_v is None or cur_v is None:
            continue
        pct = ((cur_v - prev_v) / abs(prev_v) * 100) if prev_v != 0 else None
        label = CRITERIA_INFO.get(c["name"], {}).get("label", c["name"])
        compare_rows.append(
            {
                "Kriter": label,
                "Önceki Dönem": _fmt_by_kind(d.get("format"), prev_v),
                "Bu Dönem": _fmt_by_kind(d.get("format"), cur_v),
                "Değişim": f"{pct:+.1f}%" if pct is not None else "—",
            }
        )
    if compare_rows:
        st.dataframe(pd.DataFrame(compare_rows), hide_index=True, use_container_width=True)
    else:
        st.caption("Karşılaştırılabilir (iki dönemli) sayısal kriter bulunamadı.")

    # 5) Kriter bazında "Neden?" açıklamaları
    st.markdown("**Kriter Bazında \"Neden?\" Açıklamaları**")
    for c in criteria:
        label = CRITERIA_INFO.get(c["name"], {}).get("label", c["name"])
        icon = "✅" if c["score"] == 1 else ("❌" if c["score"] == 0 else "❔")
        with st.expander(f"{icon} {label}"):
            st.markdown(build_why_explanation(c["name"], c["notes"], c["score"]))

    # 6) AI Yorumu (LLM varsa, yoksa/başarısızsa şablon fallback)
    st.markdown("**🤖 AI Yorumu**")
    st.info(_get_ai_commentary(ticker, detail))

    # 7) Ham finansal veri tablosu
    st.markdown("**Ham Finansal Veriler**")
    raw = detail.get("raw_metrics") or {}
    cur_raw, prev_raw = raw.get("cur") or {}, raw.get("prev") or {}
    ordered_keys = list(_RAW_METRIC_LABELS)
    all_keys = sorted(
        set(cur_raw) | set(prev_raw),
        key=lambda k: ordered_keys.index(k) if k in ordered_keys else len(ordered_keys),
    )
    raw_rows = []
    for key in all_keys:
        prev_v, cur_v = prev_raw.get(key), cur_raw.get(key)
        change = None
        if prev_v is not None and cur_v is not None and prev_v != 0:
            change = (cur_v - prev_v) / abs(prev_v) * 100
        raw_rows.append(
            {
                "Metrik": _RAW_METRIC_LABELS.get(key, key),
                "Önceki Dönem": f"{prev_v:,.0f}" if prev_v is not None else "—",
                "Bu Dönem": f"{cur_v:,.0f}" if cur_v is not None else "—",
                "Değişim %": f"{change:+.1f}%" if change is not None else "—",
            }
        )
    if raw_rows:
        st.dataframe(pd.DataFrame(raw_rows), hide_index=True, use_container_width=True)
    else:
        st.caption("Ham veri bulunamadı.")


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
        search = st.text_input("Hisse ara", placeholder="örn. TUPRS")
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

    # Arama kutusuna yazılan hisse tek bir eşleşmeye daraldıysa (örn. tam
    # ticker yazıldıysa), aşağıdaki seçim kutusuna dokunmaya GEREK KALMADAN
    # doğrudan o hissenin detayı gösterilir — kullanıcı geri bildirimi:
    # "2 kere seçmek istemiyorum". Arama boşsa ya da birden fazla eşleşme
    # varsa, seçim kutusu sadece o (daraltılmış) sonuçlar arasından seçtiriyor.
    detail_options = sorted(filtered["ticker"].tolist()) if search else sorted(overview["ticker"].tolist())

    if not detail_options:
        st.info("Aramanızla eşleşen bir hisse yok.")
        selected = None
    elif search and len(detail_options) == 1:
        selected = detail_options[0]
        st.caption(f"**{selected}** — tek eşleşme, detayı aşağıda:")
    else:
        selected = st.selectbox("Bir ticker seçin", detail_options)

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
        with st.expander("ℹ️ Bu skorlar nasıl hesaplanıyor? (formüller ve mantık)"):
            st.markdown(_METHODOLOGY_EXPLAINER)
        for p in _PILLAR_ORDER:
            if p in ticker_rows.index:
                score = ticker_rows.loc[p, "pillar_score"]
                score_text = f"{score:.0f}/100" if pd.notna(score) else "veri yok"
                with st.expander(f"{_PILLAR_LABELS[p]} — {score_text}"):
                    st.write(ticker_rows.loc[p, "notes"])
                    if p == "safety":
                        f_detail = _extract_f_score_detail(ticker_rows.loc[p, "f_score_detail"])
                        st.divider()
                        if f_detail:
                            render_fscore_transparency(selected, f_detail)
                        elif pd.notna(score):
                            # score VAR ama detay JSON yok -> bu özellik eklenmeden
                            # önceki bir taramadan kalma, yeniden taramak çözer.
                            # score da yoksa (örn. veri çok bayat olduğu için hiç
                            # hesaplanmadıysa) üstteki notes zaten sebebi açıklıyor
                            # — burada "yeniden taratın" demek yanıltıcı olurdu.
                            st.caption(
                                "F-Score kriter kırılımı bu kayıt için mevcut değil — "
                                "hisse bu özellik eklenmeden önce taranmış olabilir. "
                                "`python scripts/calculate_alpha_score.py` ile yeniden "
                                "taratınca görünür."
                            )
        if "profitability_ttm" in ticker_rows.index:
            score_text = f"{ttm_score:.0f}/100" if pd.notna(ttm_score) else "veri yok"
            with st.expander(f"Kârlılık (Son 12 Ay / TTM) — {score_text}"):
                st.write(ticker_rows.loc["profitability_ttm", "notes"])

        st.divider()
        render_news_section(selected)


if __name__ == "__main__":
    main()
