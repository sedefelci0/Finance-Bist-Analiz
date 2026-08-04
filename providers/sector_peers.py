"""BIST evreni içinde sektör bazlı otomatik peer grubu oluşturma.

Ticker evreni data/bist_universe.txt'ten okunur (bkz. dosyadaki UYARI —
resmi endeks kaynağından değil, elle derlenip KAP'ın ticker veritabanına
karşı tek tek doğrulanmış ~125 tanınmış/likit BIST şirketinden oluşuyor).
Sektör bilgisi yfinance_provider.fetch_market_data() içindeki 'sector'
alanından gelir (İngilizce GICS benzeri kategori, örn. "Energy",
"Industrials" — BIST'e özgü resmi bir sektör taksonomisi değil ama
elimizdeki en pratik kaynak).
"""
from __future__ import annotations

from pathlib import Path

from providers import yfinance_provider

_UNIVERSE_PATH = Path(__file__).resolve().parent.parent / "data" / "bist_universe.txt"


def load_universe(path: Path = _UNIVERSE_PATH) -> list[str]:
    """data/bist_universe.txt'ten yorum satırları ve boş satırlar hariç ticker listesini okur."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def fetch_universe_market_data(tickers: list[str]) -> dict[str, dict]:
    """Verilen ticker listesi için market_data'yı toplu çeker.

    Tek tek yfinance .info çağrısı gerektirdiğinden (BIST evreni için ~125 istek)
    biraz zaman alır. Bir CLI koşusunda BİR KEZ çağrılıp sonuç önbelleğe
    (bellekte) alınmalı — her ticker için tekrar tekrar çağırmayın.
    """
    result: dict[str, dict] = {}
    for ticker in tickers:
        try:
            result[ticker] = yfinance_provider.fetch_market_data(ticker)
        except Exception:
            continue  # tek bir ticker çekilemezse tüm taramayı durdurma
    return result


def get_sector_peers(ticker: str, universe_market_data: dict[str, dict]) -> list[dict]:
    """ticker'ın sektörüyle eşleşen evrendeki diğer şirketlerin market_data listesini döndürür.

    universe_market_data: fetch_universe_market_data() çıktısı (ticker -> market_data).
    ticker'ın kendisi de sektörü eşleşiyorsa listeye dahil edilir (percentile
    hesabını bozmaz, kendisiyle karşılaştırma zaten nötr bir etki yapar).
    """
    own = universe_market_data.get(ticker)
    sector = own.get("sector") if own else None
    if sector is None:
        return []
    return [md for md in universe_market_data.values() if md.get("sector") == sector]
