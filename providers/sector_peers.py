"""BIST evreni içinde sektör bazlı otomatik peer grubu oluşturma.

Ticker evreni İKİ kademeli bir zincirle belirlenir (bkz. load_universe):
  1. BİRİNCİL: providers/bist_universe_provider.py — Borsa İstanbul'un
     resmi Yıldız Pazar (XYLDZ) CSV'si, 24 saatlik yerel cache ile.
  2. FALLBACK: data/bist_universe.txt — elle derlenmiş, KAP'ın ticker
     veritabanına karşı tek tek doğrulanmış statik liste (CSV'ye hiç
     erişilemezse, örn. ağ hatası, kullanılır).
Sektör bilgisi yfinance_provider.fetch_market_data() içindeki 'sector'
alanından gelir (İngilizce GICS benzeri kategori, örn. "Energy",
"Industrials" — BIST'e özgü resmi bir sektör taksonomisi değil ama
elimizdeki en pratik kaynak).
"""
from __future__ import annotations

from pathlib import Path

from providers import bist_universe_provider, yfinance_provider

_STATIC_UNIVERSE_PATH = Path(__file__).resolve().parent.parent / "data" / "bist_universe.txt"


def _load_static_universe(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def load_universe(path: Path | None = None) -> list[str]:
    """BIST evrenini döndürür.

    `path` verilirse (örn. testlerde) doğrudan o statik dosyadan okunur —
    dinamik CSV zinciri devre dışı kalır. `path` verilmezse önce Borsa
    İstanbul'un güncel Yıldız Pazar CSV'sini (cache'li) dener, o başarısız
    olursa data/bist_universe.txt'e düşer.
    """
    if path is not None:
        return _load_static_universe(path)

    try:
        return bist_universe_provider.get_star_market_universe()
    except Exception as exc:
        print(f"UYARI: Borsa İstanbul evren CSV'sine erişilemedi ({exc}), statik listeye düşülüyor.")
        return _load_static_universe(_STATIC_UNIVERSE_PATH)


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
