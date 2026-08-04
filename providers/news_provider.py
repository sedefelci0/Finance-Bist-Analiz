"""Bir ticker için üç kaynaktan haber/bildirim çeker: yfinance, KAP, Google News RSS.

Bu modül skorlama pipeline'ının (normalizer/scoring/db) parçası DEĞİL — sadece
web arayüzünün "Hisse Detayı" panelinde anlık gösterim için kullanılıyor,
hiçbir sonucu veritabanına yazmıyor. Üç kaynak birbirinin fallback'i değil,
üçü de her zaman ayrı ayrı denenir ve gösterilir.

KAP kısmı kap_provider.py'deki finansal veri çekme fonksiyonlarıyla AYNI
teknik altyapıyı (Playwright headless Chromium, aynı User-Agent) kullanır
ama farklı bir veri alanına (bildirimler) baktığı için ayrı bir modülde
tutuluyor — kap_provider.py'nin sorumluluğu sadece finansal tablo kalemleri.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from xml.etree import ElementTree

import requests
import yfinance as yf
from playwright.sync_api import sync_playwright

from providers.kap_provider import _LIST_URL, _USER_AGENT

_DISCLOSURE_QUERY_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
_DISCLOSURE_DETAIL_URL = "https://www.kap.org.tr/tr/Bildirim/{index}"
_GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search?q={query}+hisse&hl=tr&gl=TR&ceid=TR:tr"


def get_company_name(ticker: str) -> str:
    """Google News araması için okunaklı şirket adı (yfinance'ten longName/shortName).

    Bulunamazsa çıplak ticker'a (.IS'siz) düşer — arama yine çalışır, sadece
    şirket adıyla aramak kadar isabetli olmayabilir.
    """
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker.removesuffix(".IS")
    except Exception:
        return ticker.removesuffix(".IS")


def fetch_yfinance_news(ticker: str, limit: int = 8) -> list[dict]:
    """yf.Ticker(ticker).news üzerinden son haberleri çeker.

    Dönüş: [{"title", "source", "date": datetime|None, "url"}, ...]
    Haber yoksa (birçok BIST hissesinde sık rastlanıyor) boş liste döner,
    hata fırlatmaz.
    """
    try:
        raw_items = yf.Ticker(ticker).news or []
    except Exception:
        return []

    results = []
    for item in raw_items:
        content = item.get("content", item)  # yfinance sürümüne göre "content" sarmalı olabilir/olmayabilir
        title = content.get("title")
        if not title:
            continue
        url = (content.get("canonicalUrl") or {}).get("url") or (content.get("clickThroughUrl") or {}).get("url")
        publisher = (content.get("provider") or {}).get("displayName", "Bilinmeyen kaynak")
        pub_date = _parse_iso_date(content.get("pubDate"))
        results.append({"title": title, "source": publisher, "date": pub_date, "url": url})

    results.sort(key=lambda r: r["date"] or datetime.min, reverse=True)
    return results[:limit]


def fetch_google_news_rss(company_name: str, limit: int = 8) -> list[dict]:
    """Google News RSS (Türkçe) üzerinden ek haber kaynağı.

    Dönüş: [{"title", "source", "date": datetime|None, "url"}, ...]
    """
    url = _GOOGLE_NEWS_RSS_URL.format(query=requests.utils.quote(company_name))
    try:
        resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=15)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.content)
    except Exception:
        return []

    results = []
    for item in root.findall(".//item"):
        title = item.findtext("title")
        if not title:
            continue
        link = item.findtext("link")
        source_el = item.find("source")
        source = source_el.text if source_el is not None else "Google News"
        pub_date = _parse_rfc822_date(item.findtext("pubDate"))
        results.append({"title": title, "source": source, "date": pub_date, "url": link})

    results.sort(key=lambda r: r["date"] or datetime.min, reverse=True)
    return results[:limit]


def get_mkk_member_oid(ticker: str) -> str | None:
    """Ticker için KAP'ın iç 'mkkMemberOid' kimliğini bulur (bildirim sorgusu için gerekli).

    get_ticker_slug_map()'ten (finansal veri sayfası için kullanılan slug)
    FARKLI bir kimlik — bildirim sorgu API'si mkkMemberOid bekliyor. Şirket
    listesi sayfasındaki gömülü JSON'dan (kaçış karakterli) regex ile çekiliyor.
    """
    bare_ticker = ticker.removesuffix(".IS")
    resp = requests.get(_LIST_URL, headers={"User-Agent": _USER_AGENT}, timeout=30)
    resp.raise_for_status()
    text = resp.text.replace('\\"', '"')  # HTML içine gömülü JSON'daki kaçışlı tırnakları düzleştir

    for match in re.finditer(
        r'"mkkMemberOid":"([^"]+)","kapMemberTitle":"[^"]*","relatedMemberTitle":(?:"[^"]*"|null),"stockCode":"([^"]*)"',
        text,
    ):
        oid, stock_codes = match.group(1), match.group(2)
        codes = [c.strip() for c in stock_codes.split(",")]
        if bare_ticker in codes:
            return oid
    return None


def fetch_kap_disclosures(ticker: str, days: int = 90, limit: int = 8) -> list[dict]:
    """Son `days` gün içindeki KAP bildirimlerini (özel durum, finansal rapor vb.) çeker.

    Dönüş: [{"title", "source": "KAP", "date": datetime|None, "url"}, ...]

    NOT: KAP'ın bildirim sorgu API'si (/tr/api/disclosure/members/byCriteria)
    düz `requests` ile engelleniyor (bkz. kap_provider.py'deki genel not) —
    bu yüzden burada da gerçek bir tarayıcı (Playwright) üzerinden istek
    atılıyor. Sayfaya gitmeye gerek yok, taze bir tarayıcı context'inin
    request API'si üzerinden doğrudan POST atmak yeterli (test edildi).
    """
    oid = get_mkk_member_oid(ticker)
    if oid is None:
        return []

    from_date = datetime.today() - timedelta(days=days)

    payload = {
        "fromDate": from_date.strftime("%Y-%m-%d"),
        "toDate": datetime.today().strftime("%Y-%m-%d"),
        "memberType": "IGS",
        "mkkMemberOidList": [oid],
        "inactiveMkkMemberOidList": [],
        "disclosureClass": "",
        "subjectList": [],
        "isLate": "",
        "mainSector": "",
        "sector": "",
        "subSector": "",
        "marketOid": "",
        "index": "",
        "bdkReview": "",
        "bdkMemberOidList": [],
        "year": "",
        "term": "",
        "ruleType": "",
        "period": "",
        "fromSrc": False,
        "srcCategory": "",
        "disclosureIndexList": [],
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(user_agent=_USER_AGENT)
                resp = context.request.post(
                    _DISCLOSURE_QUERY_URL,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json", "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu"},
                    timeout=30000,
                )
                if resp.status != 200:
                    return []
                items = resp.json()
            finally:
                browser.close()
    except Exception:
        return []

    results = []
    for item in items:
        title = item.get("subject") or item.get("summary") or "Bildirim"
        index = item.get("disclosureIndex")
        pub_date = _parse_kap_date(item.get("publishDate"))
        results.append(
            {
                "title": title,
                "source": "KAP",
                "date": pub_date,
                "url": _DISCLOSURE_DETAIL_URL.format(index=index) if index else None,
            }
        )

    results.sort(key=lambda r: r["date"] or datetime.min, reverse=True)
    return results[:limit]


def _parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_rfc822_date(value: str | None) -> datetime | None:
    if not value:
        return None
    from email.utils import parsedate_to_datetime

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _parse_kap_date(value: str | None) -> datetime | None:
    """KAP tarih formatı: '09.07.2026 14:19:46'."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        return None
