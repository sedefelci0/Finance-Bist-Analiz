"""Alpha Score v2 — 4 pillar + momentum filtresi hesaplar, pillar_scores'a yazar.

scripts/calculate_score.py'yi (salt Piotroski F-Score) BOZMADAN, onu Pillar 2
(Finansal Sağlamlık)'in bir alt bileşeni olarak kullanan yeni bir orkestrasyon
script'i. bist_fscore mantığı hâlâ providers/normalizer.py + scoring/piotroski.py
içinde, değişmedi.

PEER GRUBU: Pillar 3 (Değerleme) ve Pillar 4 (Büyüklük) percentile hesabı
için İKİ FARKLI peer grubu kullanır — ikisi de aynı grubu kullanmıyor:
  - Değerleme: AYNI SEKTÖRDEKİ (yfinance info['sector']) evren üyeleri —
    PE/PB gibi çarpanlar sektörler arası doğrudan kıyaslanamaz.
  - Büyüklük: TÜM evren — "küçük şirket primi" literatürde piyasanın
    tamamına göre tanımlanır, sektöre göre değil. (Önceden ikisi de sektör
    bazlıydı; bu, sektöründe yalnız olan şirketlerin — örn. TUPRS, evrendeki
    tek "Energy" şirketi — Büyüklük'te anlamsız bir nötr "50" almasına
    yol açıyordu.)
Evren, providers/sector_peers.py::load_universe() üzerinden gelir (öncelik:
Borsa İstanbul'un güncel Yıldız Pazar CSV'si, o erişilemezse statik
data/bist_universe.txt'e düşer). --manual-peers ile eski davranışa (peer
grubu = aynı komutta verdiğiniz diğer ticker'lar, iki pillar için de aynı)
dönebilirsiniz.

Veri akışı: normalizer (finansal kalemler) + yfinance_provider (piyasa
verisi + fiyat getirisi) + providers/sector_peers (otomatik peer grubu)
-> scoring/pillars.py (4 pillar + toplam) -> scoring/momentum.py (filtre)
-> db.save_pillar_scores
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from db import connection as db  # noqa: E402
from providers import normalizer, sector_peers, yfinance_provider  # noqa: E402
from scoring import momentum, pillars  # noqa: E402


def _fmt(score: float | None) -> str:
    return f"{score:.1f}" if score is not None else "VERİ YOK"


def _print_report(ticker: str, pillar_results: dict, total: dict, mom: dict) -> None:
    print(f"\n=== {ticker} — Alpha Score v2 ===")
    for name, weight in pillars.PILLAR_WEIGHTS.items():
        result = pillar_results[name]
        print(f"  [{name} — ağırlık %{weight * 100:.0f}] skor={_fmt(result['score'])}")
        print(f"    {result['notes']}")
    print(f"\n  TOPLAM SKOR: {_fmt(total['total_score'])}/100")
    print(f"    {total['notes']}")
    print(f"\n  Momentum: {'ZAYIF UYARI' if mom['flag'] else 'normal'}")
    print(f"    {mom['message']}")


def compute_alpha_score(
    ticker: str, market_data: dict, sector_peer_market_data: list[dict], universe_peer_market_data: list[dict]
) -> dict:
    """Tek bir ticker için tüm pillar'ları + toplamı + momentum'u hesaplar.

    market_data: bu ticker'ın kendi piyasa verisi (main()'de önceden çekilir,
    burada tekrar çekilmez — aynı veri hem kendi skoru hem peer grubu için kullanılır).

    İki AYRI peer grubu kullanılıyor:
      - sector_peer_market_data: Pillar 3 (Değerleme) için — PE/PB gibi
        çarpanlar sadece AYNI SEKTÖRDEKİ şirketlerle anlamlı karşılaştırılır
        (bankanın PE'si bankayla, rafinerinin PE'si rafineriyle).
      - universe_peer_market_data: Pillar 4 (Büyüklük) için — akademik
        literatürdeki "küçük şirket primi" (SMB) TÜM PİYASAYA göre
        tanımlanır, sektöre göre değil. Sektöre göre kısıtlarsak, sektöründe
        tek başına olan şirketler (örn. TUPRS — evrendeki tek "Energy"
        şirketi) anlamsız bir "50" (nötr) skor alır çünkü karşılaştıracak
        hiç kimse yok.
    """
    metrics, _sources = normalizer.get_financials(ticker, years=2)
    periods = sorted(metrics.keys(), reverse=True)
    if not periods:
        raise ValueError("finansal veri hiç bulunamadı")
    cur = metrics[periods[0]]
    prev = metrics[periods[1]] if len(periods) > 1 else None

    pillar_results = {
        "profitability": pillars.calculate_profitability_pillar(cur),
        "safety": pillars.calculate_safety_pillar(cur, prev, market_data.get("market_cap")),
        "valuation": pillars.calculate_valuation_pillar(market_data, sector_peer_market_data),
        "size": pillars.calculate_size_pillar(market_data, universe_peer_market_data),
    }

    total = pillars.calculate_total_score({name: r["score"] for name, r in pillar_results.items()})

    returns = yfinance_provider.fetch_price_returns(ticker)
    mom = momentum.check_momentum_flag(total["total_score"], returns)

    return {"pillar_results": pillar_results, "total": total, "momentum": mom, "market_data": market_data}


def run(
    ticker: str,
    market_data: dict,
    sector_peer_market_data: list[dict],
    universe_peer_market_data: list[dict],
    engine,
    skip_db: bool,
) -> None:
    print(f"{ticker}: veri toplanıyor...")
    result = compute_alpha_score(ticker, market_data, sector_peer_market_data, universe_peer_market_data)
    _print_report(ticker, result["pillar_results"], result["total"], result["momentum"])

    if skip_db:
        return

    pillar_rows = [
        {"name": name, "score": r["score"], "weight": pillars.PILLAR_WEIGHTS[name], "notes": r["notes"]}
        for name, r in result["pillar_results"].items()
    ]
    db.save_pillar_scores(
        engine,
        ticker,
        calculation_date=date.today(),
        pillars=pillar_rows,
        total_score=result["total"]["total_score"],
        momentum_flag=result["momentum"]["flag"],
    )
    print(f"{ticker}: pillar_scores tablosuna yazıldı.")


def main() -> None:
    parser = argparse.ArgumentParser(description="BIST hisseleri için Alpha Score v2 (4 pillar + momentum) hesaplar")
    parser.add_argument("tickers", nargs="+", help="Skorlanacak ticker'lar, örn: TUPRS.IS THYAO.IS")
    parser.add_argument("--skip-db", action="store_true", help="Sadece ekrana bas, veritabanına yazma")
    parser.add_argument(
        "--manual-peers",
        action="store_true",
        help="Otomatik BIST sektör taraması yerine, peer grubu olarak sadece komut satırındaki diğer ticker'ları kullan",
    )
    args = parser.parse_args()

    engine = None
    if not args.skip_db:
        engine = db.get_engine()
        db.ensure_schema(engine)

    market_data_by_ticker: dict[str, dict] = {}
    valuation_peer_source: dict[str, list[dict]] = {}  # Pillar 3 — sektör bazlı
    size_peer_source: dict[str, list[dict]] = {}  # Pillar 4 — TÜM evren bazlı

    if args.manual_peers:
        if len(args.tickers) == 1:
            print(
                "UYARI: --manual-peers ile tek ticker verildi — valuation/size pillar'ları "
                "anlamlı bir peer grubu olmadan hesaplanacak (percentile kendisiyle "
                "karşılaştırılıp 50 çıkar).\n"
            )
        print("Piyasa verisi toplanıyor (market cap, beta, çarpanlar)...")
        for ticker in args.tickers:
            try:
                market_data_by_ticker[ticker] = yfinance_provider.fetch_market_data(ticker)
            except Exception as exc:
                print(f"{ticker}: piyasa verisi çekilemedi — {exc}", file=sys.stderr)
        # --manual-peers modunda sektör/evren ayrımı yok — komut satırındaki
        # ticker'lar her iki pillar için de aynı (tek) peer grubu.
        peers = list(market_data_by_ticker.values())
        valuation_peer_source = {ticker: peers for ticker in market_data_by_ticker}
        size_peer_source = valuation_peer_source
    else:
        universe = sector_peers.load_universe()
        print(f"BIST evreni taranıyor ({len(universe)} ticker, sektör bilgisi için)...")
        universe_market_data = sector_peers.fetch_universe_market_data(universe)
        all_universe_peers = list(universe_market_data.values())

        for ticker in args.tickers:
            if ticker in universe_market_data:
                market_data_by_ticker[ticker] = universe_market_data[ticker]
            else:
                try:
                    market_data_by_ticker[ticker] = yfinance_provider.fetch_market_data(ticker)
                except Exception as exc:
                    print(f"{ticker}: piyasa verisi çekilemedi — {exc}", file=sys.stderr)
                    continue

            # Değerleme (Pillar 3): sadece AYNI SEKTÖRDEKİ şirketlerle kıyasla
            # — PE/PB gibi çarpanlar sektörler arası doğrudan kıyaslanamaz.
            sector_peer_group = sector_peers.get_sector_peers(
                ticker, {**universe_market_data, ticker: market_data_by_ticker[ticker]}
            )
            valuation_peer_source[ticker] = sector_peer_group
            if len(sector_peer_group) < 2:
                print(f"{ticker}: UYARI — evrende aynı sektörden yeterli peer bulunamadı (n={len(sector_peer_group)}).")

            # Büyüklük (Pillar 4): TÜM evrenle kıyasla — "küçük şirket primi"
            # sektöre göre değil piyasanın tamamına göre tanımlanan bir
            # kavram. Sektöre kısıtlarsak, sektöründe yalnız olan şirketler
            # (örn. TUPRS — evrendeki tek "Energy" şirketi) karşılaştıracak
            # kimse bulamayıp anlamsız bir nötr "50" skoru alıyordu.
            size_peer_source[ticker] = all_universe_peers
            if len(all_universe_peers) < 5:
                print(f"{ticker}: UYARI — tüm evrende bile çok az peer var (n={len(all_universe_peers)}).")

    for ticker in args.tickers:
        if ticker not in market_data_by_ticker:
            continue  # piyasa verisi çekilemedi, yukarıda zaten hata basıldı
        try:
            run(
                ticker,
                market_data_by_ticker[ticker],
                valuation_peer_source.get(ticker, []),
                size_peer_source.get(ticker, []),
                engine,
                args.skip_db,
            )
        except Exception as exc:
            print(f"{ticker}: HATA — {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
