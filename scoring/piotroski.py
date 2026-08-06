"""Piotroski F-Score (9 kriter).

Not: ROA ve aktif devir hızı hesaplamalarında dönem sonu (ending) toplam
varlık kullanılıyor — literatürdeki bazı varyantlarda dönem ortalaması
kullanılır, ama iki dönemlik veriyle (bu MVP'nin kapsamı) ortalama almak
için üçüncü bir dönem gerekir. Bu, yaygın kullanılan basitleştirilmiş
varyanttır; sonuçlar buna göre yorumlanmalı.

Kaynak: Piotroski, J. (2000), "Value Investing: The Use of Historical
Financial Statement Information to Separate Winners from Losers".

ŞEFFAFLIK: Her kriter fonksiyonu (score, notes) ikilisinin yanına bir de
`detail` sözlüğü döndürür — kullanılan HAM sayısal değerleri (ve nasıl
gösterileceklerini) taşır. Bu, hesaplama MANTIĞINI değiştirmez (karşılaştırma
ifadeleri — örn. `roa_cur > roa_prev` — aynen duruyor), sadece UI katmanının
(app.py) "neden bu puan?" sorusuna cevap verebilmesi için ara sonuçları
dışarı açar. `detail["kind"]`:
  - "single": tek bir değer (örn. net_income). {"format", "cur"}
  - "compare_periods": aynı metriğin geçen yıl/bu yıl karşılaştırması.
    {"format", "prev", "cur"}
  - "compare_metrics": aynı dönemde iki FARKLI metriğin karşılaştırması
    (örn. CFO vs net kâr). {"format", "a_label", "a", "b_label", "b"}
`format`: "currency" | "percent" | "ratio" | "count" — app.py bu bilgiyle
sayıları biçimlendiriyor.
"""
from __future__ import annotations

from datetime import date

Metrics = dict[str, float | None]


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _roa(m: Metrics) -> float | None:
    return _safe_div(m.get("net_income"), m.get("total_assets"))


def _current_ratio(m: Metrics) -> float | None:
    return _safe_div(m.get("current_assets"), m.get("current_liabilities"))


def _leverage(m: Metrics) -> float | None:
    return _safe_div(m.get("long_term_debt"), m.get("total_assets"))


def _gross_margin(m: Metrics) -> float | None:
    return _safe_div(m.get("gross_profit"), m.get("revenue"))


def _asset_turnover(m: Metrics) -> float | None:
    return _safe_div(m.get("revenue"), m.get("total_assets"))


def _crit_net_income_positive(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    ni = cur.get("net_income")
    if ni is None:
        return None, "veri yok: net_income eksik", {"kind": "single", "format": "currency", "cur": None}
    return (
        (1 if ni > 0 else 0),
        f"net_income = {ni:,.0f}",
        {"kind": "single", "format": "currency", "cur": ni},
    )


def _crit_cfo_positive(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    cfo = cur.get("operating_cash_flow")
    if cfo is None:
        return None, "veri yok: operating_cash_flow eksik", {"kind": "single", "format": "currency", "cur": None}
    return (
        (1 if cfo > 0 else 0),
        f"operating_cash_flow = {cfo:,.0f}",
        {"kind": "single", "format": "currency", "cur": cfo},
    )


def _crit_roa_change(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    empty = {"kind": "compare_periods", "format": "percent", "prev": None, "cur": None}
    if prev is None:
        return None, "veri yok: önceki dönem yok", empty
    roa_cur, roa_prev = _roa(cur), _roa(prev)
    if roa_cur is None or roa_prev is None:
        return None, "veri yok: ROA hesaplanamadı (net_income veya total_assets eksik)", empty
    return (
        (1 if roa_cur > roa_prev else 0),
        f"ROA {roa_prev:.2%} -> {roa_cur:.2%}",
        {"kind": "compare_periods", "format": "percent", "prev": roa_prev, "cur": roa_cur},
    )


def _crit_cfo_greater_than_ni(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    cfo, ni = cur.get("operating_cash_flow"), cur.get("net_income")
    empty = {"kind": "compare_metrics", "format": "currency", "a_label": "Faaliyet Nakit Akışı", "a": None, "b_label": "Net Kâr", "b": None}
    if cfo is None or ni is None:
        return None, "veri yok: operating_cash_flow veya net_income eksik", empty
    return (
        (1 if cfo > ni else 0),
        f"operating_cash_flow ({cfo:,.0f}) vs net_income ({ni:,.0f})",
        {"kind": "compare_metrics", "format": "currency", "a_label": "Faaliyet Nakit Akışı", "a": cfo, "b_label": "Net Kâr", "b": ni},
    )


def _crit_leverage_change(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    empty = {"kind": "compare_periods", "format": "percent", "prev": None, "cur": None}
    if prev is None:
        return None, "veri yok: önceki dönem yok", empty
    lev_cur, lev_prev = _leverage(cur), _leverage(prev)
    if lev_cur is None or lev_prev is None:
        return None, "veri yok: uzun vadeli borç/aktif oranı hesaplanamadı", empty
    return (
        (1 if lev_cur < lev_prev else 0),
        f"uzun vadeli borç/aktif {lev_prev:.2%} -> {lev_cur:.2%}",
        {"kind": "compare_periods", "format": "percent", "prev": lev_prev, "cur": lev_cur},
    )


def _crit_current_ratio_change(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    empty = {"kind": "compare_periods", "format": "ratio", "prev": None, "cur": None}
    if prev is None:
        return None, "veri yok: önceki dönem yok", empty
    cr_cur, cr_prev = _current_ratio(cur), _current_ratio(prev)
    if cr_cur is None or cr_prev is None:
        return None, "veri yok: cari oran hesaplanamadı", empty
    return (
        (1 if cr_cur > cr_prev else 0),
        f"cari oran {cr_prev:.2f} -> {cr_cur:.2f}",
        {"kind": "compare_periods", "format": "ratio", "prev": cr_prev, "cur": cr_cur},
    )


def _crit_shares_not_diluted(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    empty = {"kind": "compare_periods", "format": "count", "prev": None, "cur": None}
    if prev is None:
        return None, "veri yok: önceki dönem yok", empty
    shares_cur, shares_prev = cur.get("shares_outstanding"), prev.get("shares_outstanding")
    if shares_cur is None or shares_prev is None:
        return None, "veri yok: hisse sayısı verisi yok", empty
    return (
        (1 if shares_cur <= shares_prev else 0),
        f"hisse sayısı {shares_prev:,.0f} -> {shares_cur:,.0f}",
        {"kind": "compare_periods", "format": "count", "prev": shares_prev, "cur": shares_cur},
    )


def _crit_gross_margin_change(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    empty = {"kind": "compare_periods", "format": "percent", "prev": None, "cur": None}
    if prev is None:
        return None, "veri yok: önceki dönem yok", empty
    gm_cur, gm_prev = _gross_margin(cur), _gross_margin(prev)
    if gm_cur is None or gm_prev is None:
        return None, "veri yok: brüt kar marjı hesaplanamadı", empty
    return (
        (1 if gm_cur > gm_prev else 0),
        f"brüt kar marjı {gm_prev:.2%} -> {gm_cur:.2%}",
        {"kind": "compare_periods", "format": "percent", "prev": gm_prev, "cur": gm_cur},
    )


def _crit_asset_turnover_change(cur: Metrics, prev: Metrics | None) -> tuple[int | None, str, dict]:
    empty = {"kind": "compare_periods", "format": "ratio", "prev": None, "cur": None}
    if prev is None:
        return None, "veri yok: önceki dönem yok", empty
    at_cur, at_prev = _asset_turnover(cur), _asset_turnover(prev)
    if at_cur is None or at_prev is None:
        return None, "veri yok: aktif devir hızı hesaplanamadı", empty
    return (
        (1 if at_cur > at_prev else 0),
        f"aktif devir hızı {at_prev:.2f} -> {at_cur:.2f}",
        {"kind": "compare_periods", "format": "ratio", "prev": at_prev, "cur": at_cur},
    )


_CRITERIA = [
    ("net_kar_pozitif", _crit_net_income_positive),
    ("faaliyet_nakit_akisi_pozitif", _crit_cfo_positive),
    ("roa_degisimi", _crit_roa_change),
    ("nakit_akisi_net_kardan_buyuk", _crit_cfo_greater_than_ni),
    ("uzun_vadeli_borc_azalisi", _crit_leverage_change),
    ("cari_oran_iyilesmesi", _crit_current_ratio_change),
    ("hisse_sayisi_sulanmadi", _crit_shares_not_diluted),
    ("brut_kar_marji_iyilesmesi", _crit_gross_margin_change),
    ("aktif_devir_hizi_iyilesmesi", _crit_asset_turnover_change),
]


def calculate_f_score(metrics: dict[date, Metrics]) -> dict:
    """metrics: normalizer.get_financials()'in döndürdüğü {period_date: {metric: value}}.

    En az iki dönem gerektiren kriterler (7/9) için en güncel iki dönem kullanılır.
    Tek dönem varsa sadece tek-dönemlik kriterler (net kâr>0, CFO>0) hesaplanabilir.

    Dönüş: {
        "period_date": en güncel dönem,
        "prev_period_date": önceki dönem (yoksa None),
        "criteria": [{"name", "score" (0/1/None), "notes", "detail"}, ...],
        "total_score": int,               # None olan kriterler 0 sayılmaz, toplamdan hariç tutulur
        "calculated_count": int,          # 0/1 puan verilebilen kriter sayısı
        "unavailable_count": int,         # "veri yok" olan kriter sayısı
        "raw_metrics": {"cur": {...}, "prev": {...} | None},  # ham veri tablosu için
    }
    """
    if not metrics:
        raise ValueError("metrics boş, hesaplanacak veri yok")

    periods = sorted(metrics.keys(), reverse=True)
    cur_date = periods[0]
    cur = metrics[cur_date]
    prev_date = periods[1] if len(periods) > 1 else None
    prev = metrics[prev_date] if prev_date is not None else None

    criteria_results = []
    for name, fn in _CRITERIA:
        score, notes, detail = fn(cur, prev)
        criteria_results.append({"name": name, "score": score, "notes": notes, "detail": detail})

    calculated = [c for c in criteria_results if c["score"] is not None]
    total_score = sum(c["score"] for c in calculated)

    return {
        "period_date": cur_date,
        "prev_period_date": prev_date,
        "criteria": criteria_results,
        "total_score": total_score,
        "calculated_count": len(calculated),
        "unavailable_count": len(criteria_results) - len(calculated),
        "raw_metrics": {"cur": cur, "prev": prev},
    }
