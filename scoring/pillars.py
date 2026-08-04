"""Alpha Score v2 — 4 pillar + momentum filtresi.

Kaynak: Özer & Yıldırım Kutbay (2022), "Testing Multi-Factor Asset Pricing
Models in Borsa Istanbul" — q-faktör modelinin (piyasa+SMB+CMA+ROE) BIST'te
en güçlü açıklayıcı güce sahip olduğu bulgusuna dayanan 4 pillar + 1 filtre
mimarisi. Ağırlıklar |t|-istatistiği sıralamasına göre: Kârlılık %35,
Finansal Sağlamlık/Yatırım Disiplini %30, Değerleme %20, Büyüklük/Piyasa
Duyarlılığı %10; Momentum ağırlıksız bir filtre (skoru düşürmez, sadece
uyarı bayrağı — bkz. scoring/momentum.py).

ÖNEMLİ — NORMALİZASYON VARSAYIMLARI: Kullanıcı sadece Pillar 3 (Değerleme)
için sektör-percentile zorunluluğu belirtti. Pillar 1, 2 ve 4'ün mutlak
oran -> 0-100 skor dönüşümü için burada makul, tartışılabilir "anchor"
(sabit eşik) değerleri seçildi (örn. ROE %0->0 puan, %25->100 puan). Bunlar
modül başında sabit olarak tanımlı ve kolayca ayarlanabilir; BIST'e özgü
kalibrasyon (TFRS 29 enflasyon muhasebesi nominal rakamları şişirebilir)
için gözden geçirilmeleri önerilir.
"""
from __future__ import annotations

from scoring import altman_z, piotroski

Metrics = dict[str, float | None]

# --- Pillar 1: Kârlılık anchor'ları (oran -> 0-100 skor) ---
_ROE_LOW, _ROE_HIGH = 0.0, 0.25
_ROIC_LOW, _ROIC_HIGH = 0.0, 0.20
_GROSS_MARGIN_LOW, _GROSS_MARGIN_HIGH = 0.0, 0.40
_OPERATING_MARGIN_LOW, _OPERATING_MARGIN_HIGH = 0.0, 0.25

# --- Pillar 2: Finansal Sağlamlık alt-ağırlıkları ve anchor'ları ---
_SAFETY_CORE_WEIGHT = 0.50     # F-Score + Z-Score bileşik skoru
_LEVERAGE_DISCIPLINE_WEIGHT = 0.25  # uzun vadeli borç/aktif değişimi (CMA)
_CURRENT_RATIO_WEIGHT = 0.25
_LEVERAGE_CHANGE_SWING = 0.15  # ±15 puanlık oran değişimi tam skor salınımı
_CURRENT_RATIO_LOW, _CURRENT_RATIO_MID, _CURRENT_RATIO_HIGH = 0.5, 1.0, 2.0

# --- Pillar ağırlıkları (toplam skor) ---
PILLAR_WEIGHTS = {
    "profitability": 0.35,
    "safety": 0.30,
    "valuation": 0.20,
    "size": 0.10,
}


def _linear_score(value: float | None, low: float, high: float) -> float | None:
    """value'yu [low, high] aralığında 0-100'e lineer haritalar, dışına taşarsa clamp eder."""
    if value is None:
        return None
    if high == low:
        return None
    score = (value - low) / (high - low) * 100
    return max(0.0, min(100.0, score))


def percentile_rank(value: float | None, peer_values: list[float | None]) -> float | None:
    """value'nun peer_values içindeki percentile'ı (0-100, düşük=peer'lerin çoğundan küçük).

    Eşit değerler ortalama sıra yöntemiyle (mid-rank) ele alınır. value veya
    geçerli peer verisi yoksa None döner.
    """
    if value is None:
        return None
    valid_peers = [v for v in peer_values if v is not None]
    if not valid_peers:
        return None
    below = sum(1 for v in valid_peers if v < value)
    equal = sum(1 for v in valid_peers if v == value)
    rank = below + equal / 2
    return (rank / len(valid_peers)) * 100


def calculate_profitability_pillar(metrics: Metrics) -> dict:
    """Pillar 1 (%35): ROE, ROIC, brüt kar marjı, faaliyet kar marjı ortalaması."""
    net_income = metrics.get("net_income")
    total_equity = metrics.get("total_equity")
    ebit = metrics.get("ebit")
    invested_capital = metrics.get("invested_capital")
    tax_rate = metrics.get("tax_rate_for_calcs")
    gross_profit = metrics.get("gross_profit")
    revenue = metrics.get("revenue")

    roe = net_income / total_equity if net_income is not None and total_equity else None
    roic = (
        ebit * (1 - tax_rate) / invested_capital
        if ebit is not None and tax_rate is not None and invested_capital
        else None
    )
    gross_margin = gross_profit / revenue if gross_profit is not None and revenue else None
    operating_margin = ebit / revenue if ebit is not None and revenue else None

    components = {
        "roe": _linear_score(roe, _ROE_LOW, _ROE_HIGH),
        "roic": _linear_score(roic, _ROIC_LOW, _ROIC_HIGH),
        "gross_margin": _linear_score(gross_margin, _GROSS_MARGIN_LOW, _GROSS_MARGIN_HIGH),
        "operating_margin": _linear_score(operating_margin, _OPERATING_MARGIN_LOW, _OPERATING_MARGIN_HIGH),
    }
    available = {k: v for k, v in components.items() if v is not None}

    if not available:
        return {"score": None, "notes": "veri yok: ROE, ROIC, brüt/faaliyet marjı hiçbiri hesaplanamadı"}

    score = sum(available.values()) / len(available)
    missing = [k for k, v in components.items() if v is None]
    notes = f"ROE={roe:.2%} " if roe is not None else "ROE=yok "
    notes += f"ROIC={roic:.2%} " if roic is not None else "ROIC=yok "
    notes += f"brüt marj={gross_margin:.2%} " if gross_margin is not None else "brüt marj=yok "
    notes += f"faaliyet marjı={operating_margin:.2%}" if operating_margin is not None else "faaliyet marjı=yok"
    if missing:
        notes += f" ({len(missing)} bileşen veri eksikliğinden hesaba katılmadı: {', '.join(missing)})"

    return {"score": score, "notes": notes}


def calculate_safety_pillar(metrics: Metrics, prev_metrics: Metrics | None, market_cap: float | None) -> dict:
    """Pillar 2 (%30): (F-Score + Z-Score bileşik) %50, uzun vadeli borç disiplini %25, cari oran %25.

    F-Score ve Z-Score AYRI ağırlıklandırılmıyor — ikisinin normalize edilmiş
    skorlarının ortalaması "safety_core" olarak tek bir bileşen sayılıyor
    (kullanıcı notu: ikisi de kötüyse düşük, ikisi de iyiyse yüksek,
    çelişirlerse ortalanır — basit ortalama bunu doğal olarak sağlıyor).
    """
    period_dates_metrics = {}
    if prev_metrics is not None:
        # piotroski.calculate_f_score iki dönemli bir sözlük bekliyor; period_date'ler
        # burada önemli değil (sadece sıralama için), placeholder anahtarlar kullanıyoruz.
        from datetime import date as _date

        period_dates_metrics = {_date(2, 1, 1): metrics, _date(1, 1, 1): prev_metrics}
    else:
        from datetime import date as _date

        period_dates_metrics = {_date(1, 1, 1): metrics}

    f_result = piotroski.calculate_f_score(period_dates_metrics)
    f_score_normalized = (
        (f_result["total_score"] / f_result["calculated_count"]) * 100
        if f_result["calculated_count"] > 0
        else None
    )

    z_result = altman_z.calculate_altman_z(metrics, market_cap)
    z_normalized = None
    if z_result["z_score"] is not None:
        z = z_result["z_score"]
        if z <= 0:
            z_normalized = 0.0
        elif z < 1.81:
            z_normalized = (z / 1.81) * 50
        elif z < 2.99:
            z_normalized = 50 + ((z - 1.81) / (2.99 - 1.81)) * 50
        else:
            z_normalized = 100.0

    core_components = [s for s in (f_score_normalized, z_normalized) if s is not None]
    safety_core = sum(core_components) / len(core_components) if core_components else None

    # Uzun vadeli borç disiplini (CMA benzeri): oran DÜŞTÜYSE iyi.
    leverage_score = None
    if prev_metrics is not None:
        cur_assets, cur_debt = metrics.get("total_assets"), metrics.get("long_term_debt")
        prev_assets, prev_debt = prev_metrics.get("total_assets"), prev_metrics.get("long_term_debt")
        if cur_assets and prev_assets and cur_debt is not None and prev_debt is not None:
            lev_cur, lev_prev = cur_debt / cur_assets, prev_debt / prev_assets
            change = lev_prev - lev_cur  # pozitif = borç oranı azaldı = iyi
            leverage_score = _linear_score(change, -_LEVERAGE_CHANGE_SWING, _LEVERAGE_CHANGE_SWING)

    current_ratio = None
    if metrics.get("current_assets") is not None and metrics.get("current_liabilities"):
        current_ratio = metrics["current_assets"] / metrics["current_liabilities"]
    current_ratio_score = None
    if current_ratio is not None:
        if current_ratio <= _CURRENT_RATIO_LOW:
            current_ratio_score = 0.0
        elif current_ratio < _CURRENT_RATIO_MID:
            current_ratio_score = (current_ratio - _CURRENT_RATIO_LOW) / (
                _CURRENT_RATIO_MID - _CURRENT_RATIO_LOW
            ) * 50
        elif current_ratio < _CURRENT_RATIO_HIGH:
            current_ratio_score = 50 + (current_ratio - _CURRENT_RATIO_MID) / (
                _CURRENT_RATIO_HIGH - _CURRENT_RATIO_MID
            ) * 50
        else:
            current_ratio_score = 100.0

    weighted_parts = []
    if safety_core is not None:
        weighted_parts.append((safety_core, _SAFETY_CORE_WEIGHT))
    if leverage_score is not None:
        weighted_parts.append((leverage_score, _LEVERAGE_DISCIPLINE_WEIGHT))
    if current_ratio_score is not None:
        weighted_parts.append((current_ratio_score, _CURRENT_RATIO_WEIGHT))

    if not weighted_parts:
        return {"score": None, "notes": "veri yok: F-Score, Z-Score, kaldıraç değişimi, cari oran hiçbiri hesaplanamadı"}

    total_weight = sum(w for _, w in weighted_parts)
    score = sum(s * w for s, w in weighted_parts) / total_weight

    notes = (
        f"F-Score={f_result['total_score']}/{f_result['calculated_count']} "
        f"({'normalize: %.0f' % f_score_normalized if f_score_normalized is not None else 'yok'}); "
        f"{z_result['notes']}; "
        f"kaldıraç disiplini skoru={'%.0f' % leverage_score if leverage_score is not None else 'yok'}; "
        f"cari oran={'%.2f' % current_ratio if current_ratio is not None else 'yok'}"
    )

    return {"score": score, "notes": notes}


def calculate_valuation_pillar(market_data: dict, peer_market_data: list[dict]) -> dict:
    """Pillar 3 (%20): PE, PEG, EV/EBITDA, P/B — sektör içi percentile bazlı.

    DÜŞÜK çarpan = ucuz = YÜKSEK skor, bu yüzden 100 - percentile kullanılıyor.
    peer_market_data: aynı sektördeki şirketlerin fetch_market_data() çıktıları
    (bu ticker'ın kendisi dahil edilebilir, percentile hesabını etkilemez).
    Peer grubu bu fonksiyona dışarıdan verilir — sektör bazlı peer listesi
    toplamak (örn. yfinance info['sector'] ya da BIST30/100 taraması) ayrı bir
    adım, bu fonksiyon sadece elindeki peer verisiyle çalışır.
    """
    if market_data.get("currency_mismatch"):
        currency_note = " [UYARI: financialCurrency != currency, çarpanlar farklı para birimi karışımı olabilir]"
    else:
        currency_note = ""

    multiple_fields = ["trailing_pe", "peg_ratio", "ev_to_ebitda", "price_to_book"]
    scores = {}
    for field in multiple_fields:
        value = market_data.get(field)
        peers = [p.get(field) for p in peer_market_data]
        pct = percentile_rank(value, peers)
        scores[field] = (100 - pct) if pct is not None else None

    available = {k: v for k, v in scores.items() if v is not None}
    if not available:
        return {
            "score": None,
            "notes": f"veri yok: PE/PEG/EV-EBITDA/P-B hiçbiri hesaplanamadı (peer grubu boş olabilir){currency_note}",
        }

    score = sum(available.values()) / len(available)
    missing = [k for k, v in scores.items() if v is None]
    notes = ", ".join(
        f"{k}={'%.0f' % v if v is not None else 'yok'}" for k, v in scores.items()
    )
    notes += f" (n_peer={len(peer_market_data)})"
    if missing:
        notes += f" — eksik: {', '.join(missing)}"
    notes += currency_note

    return {"score": score, "notes": notes}


def calculate_size_pillar(market_data: dict, peer_market_data: list[dict]) -> dict:
    """Pillar 4 (%10): piyasa değeri percentile (KÜÇÜK=yüksek skor) + beta (düşük=yüksek skor).

    KARAR (kullanıcı onayı): akademik SMB (Small Minus Big) faktörünün küçük
    şirket risk primi mantığı doğrudan skora yansıtılıyor — küçük piyasa
    değeri YÜKSEK puan alır. Beta'da DÜŞÜK volatilite = yüksek skor (defansif
    eğilim, bu yön tartışmasızdı).
    """
    market_cap_pct = percentile_rank(market_data.get("market_cap"), [p.get("market_cap") for p in peer_market_data])
    market_cap_score = (100 - market_cap_pct) if market_cap_pct is not None else None
    beta_pct = percentile_rank(market_data.get("beta"), [p.get("beta") for p in peer_market_data])
    beta_score = (100 - beta_pct) if beta_pct is not None else None

    components = {"market_cap": market_cap_score, "beta": beta_score}
    available = {k: v for k, v in components.items() if v is not None}
    if not available:
        return {"score": None, "notes": f"veri yok: piyasa değeri/beta percentile hesaplanamadı (n_peer={len(peer_market_data)})"}

    score = sum(available.values()) / len(available)
    notes = (
        f"piyasa değeri (küçüklük skoru)={'%.0f' % market_cap_score if market_cap_score is not None else 'yok'}, "
        f"beta={market_data.get('beta')} (skor={'%.0f' % beta_score if beta_score is not None else 'yok'}), "
        f"n_peer={len(peer_market_data)}"
    )
    return {"score": score, "notes": notes}


def calculate_total_score(pillar_scores: dict[str, float | None]) -> dict:
    """4 pillar skorunu PILLAR_WEIGHTS ile ağırlıklandırıp 0-100 toplam skor üretir.

    Eksik pillar'lar toplam ağırlıktan düşülür (mevcut pillar'lar üzerinden
    yeniden normalize edilir) — tek bir eksik pillar tüm skoru None yapmaz,
    ama notes'ta hangi pillar'ların eksik olduğu açıkça belirtilir.
    """
    weighted_parts = [
        (pillar_scores[name], weight)
        for name, weight in PILLAR_WEIGHTS.items()
        if pillar_scores.get(name) is not None
    ]
    missing = [name for name in PILLAR_WEIGHTS if pillar_scores.get(name) is None]

    if not weighted_parts:
        return {"total_score": None, "notes": "veri yok: hiçbir pillar hesaplanamadı"}

    total_weight = sum(w for _, w in weighted_parts)
    total = sum(s * w for s, w in weighted_parts) / total_weight

    notes = ", ".join(f"{name}={pillar_scores.get(name):.0f}" if pillar_scores.get(name) is not None else f"{name}=yok" for name in PILLAR_WEIGHTS)
    if missing:
        notes += f" — eksik pillar(lar) ağırlıklardan çıkarılıp kalanlar yeniden normalize edildi: {', '.join(missing)}"

    return {"total_score": total, "notes": notes}
