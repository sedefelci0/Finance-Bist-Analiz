"""BIST Yıldız Pazar'a yeni eklenen/çıkarılan şirketleri tespit eder.

Bağımsız çalıştırılabilir bir script — zamanlaması (cron, GitHub Actions,
manuel) ayrıca kurulmalı, burada sadece "çalıştırıldığında ne yapar" var:

    python scripts/check_new_listings.py

NOT: Alpha Score toplu taraması (calculate_alpha_score.py) zaten HER
ÇALIŞTIRMADA providers/bist_universe_provider.py üzerinden güncel Yıldız
Pazar listesini (24 saatlik cache ile) çekiyor — yani yeni bir şirket
listelendiğinde bir sonraki normal skorlama koşusu onu OTOMATİK olarak
kapsıyor, ayrı bir "ekleme" adımına gerek yok. Bu script'in asıl işi:
  1. Değişikliği İNSANA BİLDİRMEK (konsola yazdırmak) — yeni bir halka arz
     olduğunda haberdar olmak için elle CSV'ye bakmanıza gerek kalmasın.
  2. data/known_tickers.txt'i (git'e commit'lenen, kalıcı referans listesi)
     güncel duruma getirmek — bir sonraki koşunun doğru diff alabilmesi için.
  3. data/bist_universe.txt'i (dinamik CSV'ye hiç erişilemediği durumlardaki
     ACİL DURUM fallback listesi) güncel anlık görüntüyle tazelemek — bu
     dosya elle bakım gerektirmesin diye buradan otomatik besleniyor.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from providers import bist_universe_provider  # noqa: E402

_KNOWN_TICKERS_PATH = Path(__file__).resolve().parent.parent / "data" / "known_tickers.txt"
_STATIC_FALLBACK_PATH = Path(__file__).resolve().parent.parent / "data" / "bist_universe.txt"


def _read_known_tickers() -> set[str] | None:
    """İlk çalıştırmada dosya yoktur -> None döner (henüz bir temel/baseline yok)."""
    if not _KNOWN_TICKERS_PATH.exists():
        return None
    lines = _KNOWN_TICKERS_PATH.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.strip().startswith("#")}


def _write_known_tickers(tickers: set[str]) -> None:
    header = (
        f"# BIST Yıldız Pazar bilinen ticker listesi — scripts/check_new_listings.py "
        f"tarafından {date.today().isoformat()} tarihinde güncellendi.\n"
        "# Bu dosya git'e commit'lenir: değişiklikler git geçmişinde bir denetim izi oluşturur.\n"
    )
    content = header + "\n".join(sorted(tickers)) + "\n"
    _KNOWN_TICKERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _KNOWN_TICKERS_PATH.write_text(content, encoding="utf-8")


def _write_static_fallback(tickers: set[str]) -> None:
    header = (
        "# BIST evreni — Borsa İstanbul'un Yıldız Pazar (XYLDZ) CSV'sinden otomatik\n"
        f"# üretildi (scripts/check_new_listings.py, {date.today().isoformat()}).\n"
        "# Bu dosya sadece dinamik CSV kaynağına HİÇ erişilemediği durumlarda (ağ\n"
        "# hatası) acil durum fallback'i olarak kullanılır — bkz.\n"
        "# providers/sector_peers.py::load_universe(). Elle düzenlemeyin, bu script\n"
        "# çalıştırıldıkça üzerine yazılır.\n"
    )
    content = header + "\n".join(sorted(tickers)) + "\n"
    _STATIC_FALLBACK_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    print("Borsa İstanbul Yıldız Pazar listesi çekiliyor (taze veri, 24 saatlik cache atlanıyor)...")
    # fetch_star_market_tickers() cache'e hiç bakmadan doğrudan CSV'yi çeker
    # (cache mantığı sadece get_star_market_universe() içinde) — haftalık
    # kontrolün amacı zaten güncelliği yakalamak olduğu için burada bilerek
    # bunu kullanıyoruz.
    current = set(bist_universe_provider.fetch_star_market_tickers())
    bist_universe_provider._write_cache(sorted(current))  # normal skorlama koşuları da taze veriden yararlansın

    known = _read_known_tickers()

    if known is None:
        print(f"İlk çalıştırma: henüz bir temel liste yok. {len(current)} ticker temel olarak kaydediliyor.")
        _write_known_tickers(current)
        _write_static_fallback(current)
        return

    added = current - known
    removed = known - current

    if not added and not removed:
        print(f"Değişiklik yok. Yıldız Pazar'da hâlâ {len(current)} şirket var.")
        return

    if added:
        print(f"\n YENİ EKLENEN {len(added)} ticker:")
        for t in sorted(added):
            print(f"  + {t}")
    if removed:
        print(f"\n LİSTEDEN ÇIKARILAN {len(removed)} ticker:")
        for t in sorted(removed):
            print(f"  - {t}")

    _write_known_tickers(current)
    _write_static_fallback(current)
    print(
        f"\ndata/known_tickers.txt ve data/bist_universe.txt güncellendi. "
        "Bu değişikliği görmek/izlemek isterseniz commit'leyin."
    )


if __name__ == "__main__":
    main()
