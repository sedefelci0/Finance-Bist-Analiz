"""KAP (kap.org.tr) üzerinden finansal tablo kalemlerini çeker — yfinance fallback'i.

ÖNEMLİ NOT (mimari kısıtlama): KAP'ın /tr/api/* uç noktaları bot korumasıyla
tamamen engelleniyor (test edildi: hem GET hem POST istekleri sessizce timeout
oluyor, 404 bile dönmüyor). Şirket finansal bilgi sayfası da içeriği JavaScript
ile sayfa yüklendikten sonra o engellenen API'den çekiyor; yani düz `requests`
ile ham HTML'de finansal rakamlar YOK. Bu yüzden bu modül gerçek bir tarayıcıyı
(Playwright/Chromium) headless çalıştırıp sayfayı JS ile render ettirip
sonucu DOM'dan okuyor. Bu nedenle `pip install playwright` sonrası ayrıca
`playwright install chromium` çalıştırılması gerekiyor.

Şirket listesi sayfası (bist-sirketler) statik HTML olduğu için ticker -> KAP
slug eşlemesi düz `requests` ile çekiliyor, tarayıcıya gerek yok.
"""
from __future__ import annotations

import calendar
import re
from datetime import date

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_LIST_URL = "https://www.kap.org.tr/tr/bist-sirketler"
_FINANCIALS_URL = "https://www.kap.org.tr/tr/sirket-finansal-bilgileri/{slug}"

# yfinance_provider._LABEL_CANDIDATES ile aynı kanonik alan adlarına karşılık
# gelen KAP'ın (Türkçe XBRL) tablo satır etiketleri. Şirketler arası ufak
# etiket farklarına karşı birden fazla varyant deneniyor. Karşılaştırma
# _normalize_label() ile yapıldığı için "kar"/"kâr" gibi aksan farkları
# otomatik eşleşir — burada yine de en olası biçimleri yazıyoruz.
#
# NOT: operating_cash_flow, shares_outstanding, retained_earnings,
# invested_capital ve tax_rate_for_calcs bu sayfada YOK. KAP'ın
# "sirket-finansal-bilgileri" sayfası sadece özet Finansal Durum Tablosu
# (bilanço) ve Kar veya Zarar Tablosu (gelir tablosu) içeriyor; nakit akış
# tablosu, hisse sayısı ve bilançonun "Geçmiş Yıllar Kârları" gibi detay
# kalemleri bu görünümde hiç sunulmuyor (ayrı bir bildirim/XBRL görüntüleyici
# gerektiriyor, MVP kapsamı dışında). Bu alanlar için tek kaynak yfinance'tir
# — financialCurrency TRY olmayan tickerlarda (bkz. yfinance_provider) bu
# alanlar hep "veri yok" kalacak ve buna bağlı hesaplamalar (örn. Altman
# Z-Score'un B bileşeni) yapılamayacak.
_LABEL_CANDIDATES: dict[str, list[str]] = {
    "net_income": ["Net Dönem Karı (Zararı)", "Dönem Net Karı/Zararı", "Net Dönem Karı/Zararı", "Dönem Karı (Zararı)"],
    "total_assets": ["Varlıklar", "Toplam Varlıklar"],
    "current_assets": ["Dönen Varlıklar"],
    "current_liabilities": ["Kısa Vadeli Yükümlülükler"],
    "long_term_debt": ["Uzun Vadeli Borçlanmalar", "Uzun Vadeli Yükümlülükler"],
    "gross_profit": ["Brüt Kar (Zarar)", "Ticari Faaliyetlerden Brüt Kar (Zarar)"],
    "revenue": ["Hasılat", "Satış Gelirleri"],
    "total_equity": ["Ana Ortaklığa Ait Özkaynaklar", "Toplam Özkaynaklar"],
    "total_liabilities": ["Toplam Yükümlülükler"],
    # KAP'ta ayrı bir "EBIT" satırı yok; "Esas Faaliyet Karı (Zararı)" en
    # yakın yaklaşımdır (faiz ve vergi hariç ama bazı finansman-dışı
    # gelir/giderleri de dışarıda bırakır — yfinance'in EBIT'inden biraz
    # farklı olabilir, bu yüzden kaynağı "kap" olan ebit değerleri notes'ta
    # ayrıca işaretlenir).
    "ebit": ["Esas Faaliyet Karı (Zararı)"],
}

_DIACRITIC_NORMALIZE = str.maketrans("âÂîÎûÛ", "aAiIuU")


def _normalize_label(text: str) -> str:
    """KAP etiketlerinde 'kar'/'kâr' gibi tutarsız aksan kullanımını normalize eder."""
    return text.strip().translate(_DIACRITIC_NORMALIZE)


def get_ticker_slug_map() -> dict[str, str]:
    """Tüm BIST şirketleri için {TICKER: kap-slug} eşlemesini döndürür.

    Statik HTML sayfasından tek seferde çekilir. Birden fazla ticker için KAP
    verisi çekecek çağıranlar (örn. BIST 30 taraması) bu haritayı BİR KEZ alıp
    tekrar kullanmalı — her ticker için ayrı ayrı çağırmak 1.5MB'lık listeyi
    gereksiz yere tekrar tekrar indirir.
    """
    resp = requests.get(_LIST_URL, headers={"User-Agent": _USER_AGENT}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Her ticker <div> içinde ayrı ayrı geliyor. Çoklu hisse sınıflı şirketlerde
    # (örn. Garanti Bankası: GARAN + TGB) BİRDEN FAZLA <div> aynı <a> içinde
    # olabiliyor — a.get_text() bunları "GARAN TGB" gibi birleştirip regex'i
    # kırıyordu ve o şirketleri (birkaç büyük banka dahil) sessizce atlıyordu.
    # Her <div>'i ayrı bir aday olarak değerlendiriyoruz.
    mapping: dict[str, str] = {}
    for a in soup.select('a[href^="/tr/sirket-bilgileri/ozet/"]'):
        divs = a.find_all("div")
        candidates = [d.get_text(strip=True) for d in divs] if divs else [a.get_text(strip=True)]
        slug = a["href"].removeprefix("/tr/sirket-bilgileri/ozet/")
        for ticker in candidates:
            if ticker and re.fullmatch(r"[A-Z0-9]{3,6}", ticker):
                mapping[ticker] = slug
    return mapping


def _parse_turkish_number(text: str) -> float | None:
    text = text.strip()
    if not text or text in ("-", "—"):
        return None
    # KAP: binlik ayraç '.', ondalık ayraç ','
    cleaned = text.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _period_label_to_date(label: str) -> date | None:
    """'2025/12' -> date(2025, 12, 31). Yıl sonu (12) olmayan ara dönemleri de
    (çeyrek raporları) döndürür; hangi dönemlerin kullanılacağına çağıran karar verir."""
    match = re.fullmatch(r"(\d{4})/(\d{2})", label.strip())
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def _fetch_rendered_financial_table_html(slug: str, timeout_ms: int = 45000) -> str:
    # "networkidle" KAP'ta güvenilir değil: arka planda bitmeyen bağlantılar
    # yüzünden hep timeout'a düşüyor. Bunun yerine DOM yüklendikten sonra
    # tablonun kendisinin görünmesini bekliyoruz.
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=_USER_AGENT)
            page.goto(_FINANCIALS_URL.format(slug=slug), wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector("table tbody tr", timeout=timeout_ms)
            page.wait_for_timeout(1500)  # tüm satırların hydrate olması için ek bekleme
            return page.content()
        finally:
            browser.close()


def fetch_annual_financials(ticker: str, slug: str | None = None) -> dict[date, dict[str, float | None]]:
    """Belirtilen ticker için KAP'tan yıl sonu (Aralık) dönem kalemlerini çeker.

    `slug` verilmezse get_ticker_slug_map() ile bulunur (tek ticker için pratik,
    toplu taramada slug'ı önceden bulup geçirin).
    """
    if slug is None:
        bare_ticker = ticker.removesuffix(".IS")  # yfinance ".IS" ekler, KAP eklemez
        slug = get_ticker_slug_map().get(bare_ticker)
        if slug is None:
            raise ValueError(f"KAP'ta '{ticker}' için şirket bulunamadı")

    html = _fetch_rendered_financial_table_html(slug)
    soup = BeautifulSoup(html, "html.parser")

    # Sayfada tek bir tablo yok: Finansal Durum Tablosu (bilanço) ve Kar veya
    # Zarar Tablosu (gelir tablosu) ayrı <table> elemanları olarak geliyor.
    # (Nakit akış tablosu bu sayfada hiç yok — KAP bunu yalnızca ayrı bir
    # bildirim/XBRL görüntüleyicide sunuyor, o yüzden operating_cash_flow
    # KAP fallback'inden gelmez, sadece yfinance'ten gelebilir.)
    results: dict[date, dict[str, float | None]] = {}

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        header_cells = rows[0].find_all(["th", "td"])
        period_dates: list[date | None] = [_period_label_to_date(c.get_text()) for c in header_cells]
        if not any(period_dates):
            continue

        # "Sunum Para Birimi" satırı değerlerin hangi birimde olduğunu söyler
        # (KAP genelde "1000000TL" -> milyon TL cinsinden gösterir). yfinance
        # ham TL kullandığı için KAP değerlerini de ham TL'ye çeviriyoruz.
        multiplier = 1.0
        for row in rows:
            cells = row.find_all("td")
            if cells and cells[0].get_text(strip=True) == "Sunum Para Birimi" and len(cells) > 1:
                digits = re.match(r"(\d+)", cells[1].get_text(strip=True))
                if digits:
                    multiplier = float(digits.group(1))
                break

        # Önce bu tablodaki her satır etiketini değerlerine eşle. Bazı kalemler
        # için birden fazla aday etiket aynı tabloda satır olarak bulunabilir
        # (örn. "Brüt Kar (Zarar)" hem toplam hem "Ticari Faaliyetlerden ..."
        # alt kalemi olarak geçebilir) — bu yüzden ilk-satır-kazanır yerine
        # _LABEL_CANDIDATES'teki öncelik sırasına göre seçim yapıyoruz.
        label_to_values: dict[str, list] = {}
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            label_to_values[_normalize_label(cells[0].get_text(strip=True))] = cells[1:]

        for metric_name, candidates in _LABEL_CANDIDATES.items():
            for label in candidates:
                label = _normalize_label(label)
                if label not in label_to_values:
                    continue
                for period_date, cell in zip(period_dates, label_to_values[label]):
                    # Sadece yıl sonu (Aralık) dönemlerini tutuyoruz — Piotroski
                    # yıllık karşılaştırma kullanıyor, ara dönem verisi bu MVP'de gereksiz.
                    if period_date is None or period_date.month != 12:
                        continue
                    value = _parse_turkish_number(cell.get_text())
                    if value is not None:
                        value *= multiplier
                    results.setdefault(period_date, {}).setdefault(metric_name, value)
                break  # bu metrik için ilk uygun aday etiket kullanıldı

    return results
