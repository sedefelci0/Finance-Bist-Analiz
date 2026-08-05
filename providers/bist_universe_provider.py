"""Borsa İstanbul'un resmi Yıldız Pazar (XYLDZ) bileşen listesini çeker.

data/bist_universe.txt'in (elle derlenmiş, doğrulama gerektiren statik liste)
yerini alan BİRİNCİL kaynak — Borsa İstanbul'un herkese açık CSV'sinden her
çalıştırmada (24 saatlik yerel cache ile) güncel Yıldız Pazar bileşenlerini
çeker. CSV'ye erişilemezse (ağ hatası, format değişikliği) eski cache'e, o da
yoksa statik data/bist_universe.txt'e düşülür — bu fallback zinciri
providers/sector_peers.py::load_universe() içinde yönetiliyor.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from pathlib import Path

import requests

_CSV_URL = "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"
_INDEX_CODE = "XYLDZ"  # Yıldız Pazar
_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "bist_universe_cache.txt"
_CACHE_TTL = timedelta(hours=24)


def fetch_star_market_tickers() -> list[str]:
    """CSV'yi indirir, XYLDZ (Yıldız Pazar) bileşenlerini ayıklar, .IS uzantılı ticker listesi döner.

    CSV'nin ilk iki satırı başlık (biri Türkçe, biri İngilizce sütun adları)
    — üçüncü sütun (ENDEKS KODU / INDEX CODE) ile filtreleniyor. Borsa
    İstanbul ticker'ları ".E" ekiyle veriyor (örn. "TUPRS.E"); yfinance
    ".IS" bekliyor, o yüzden çeviriyoruz.

    Ağ hatası veya beklenmeyen format durumunda İSTİSNA fırlatır (sessizce
    boş liste dönmüyor) — çağıran taraf (get_star_market_universe) bunu
    yakalayıp cache/statik listeye düşüyor.
    """
    resp = requests.get(_CSV_URL, timeout=30)
    resp.raise_for_status()
    text = resp.content.decode("utf-8")
    reader = csv.reader(io.StringIO(text), delimiter=";")

    tickers = []
    for row in reader:
        if len(row) < 3:
            continue
        code, index_code = row[0].strip(), row[2].strip()
        if index_code != _INDEX_CODE or not code.endswith(".E"):
            continue
        tickers.append(code.removesuffix(".E") + ".IS")

    if not tickers:
        raise ValueError(
            f"CSV'de '{_INDEX_CODE}' endeksine ait hiç ticker bulunamadı — "
            "Borsa İstanbul CSV formatını değiştirmiş olabilir, kontrol edin"
        )
    return sorted(set(tickers))


def _read_cache(*, allow_stale: bool) -> list[str] | None:
    if not _CACHE_PATH.exists():
        return None
    if not allow_stale:
        age = datetime.now() - datetime.fromtimestamp(_CACHE_PATH.stat().st_mtime)
        if age > _CACHE_TTL:
            return None
    lines = _CACHE_PATH.read_text(encoding="utf-8").splitlines()
    tickers = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    return tickers or None


def _write_cache(tickers: list[str]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# Borsa İstanbul XYLDZ (Yıldız Pazar) — otomatik önbellek, "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')} itibarıyla çekildi.\n"
        f"# Kaynak: {_CSV_URL}\n"
        f"# {int(_CACHE_TTL.total_seconds() // 3600)} saatten eskiyse bir sonraki "
        "çalıştırmada otomatik yenilenir. Elle düzenlemeyin.\n"
    )
    _CACHE_PATH.write_text(header + "\n".join(tickers) + "\n", encoding="utf-8")


def get_star_market_universe() -> list[str]:
    """24 saatlik cache'e bakar, yoksa/eskiyse CSV'yi tekrar çeker ve cache'i günceller.

    CSV erişilemezse (ağ hatası, format değişikliği) süresi dolmuş olsa bile
    eski cache'e düşer — hiç veri döndürememekten iyidir. Cache hiç yoksa
    (ilk çalıştırma + ağ hatası) ValueError fırlatır; çağıran taraf
    (sector_peers.load_universe) statik data/bist_universe.txt'e düşmeli.
    """
    fresh = _read_cache(allow_stale=False)
    if fresh is not None:
        return fresh

    try:
        tickers = fetch_star_market_tickers()
        _write_cache(tickers)
        return tickers
    except Exception:
        stale = _read_cache(allow_stale=True)
        if stale is not None:
            return stale
        raise
