"""Momentum filtresi — ağırlıklı bir pillar DEĞİL, sadece bir uyarı bayrağı.

Kullanıcı notu: toplam skor yüksek (>70) ama son 6 ayda getiri belirgin
negatifse (< -%20), "momentum zayıf" uyarısı gösterilir ama toplam skoru
DÜŞÜRMEZ. Akademik gerekçe: CAR (momentum) faktörü Özer & Yıldırım Kutbay
(2022) çalışmasında istatistiksel olarak anlamlı ama en zayıf ve BIST'te
tutarsız faktör (t=7.16) — bu yüzden ağırlıklı bir pillar olarak değil,
sadece bilgilendirici bir filtre olarak kullanılıyor.
"""
from __future__ import annotations

_TOTAL_SCORE_THRESHOLD = 70.0
_RETURN_6M_THRESHOLD = -20.0


def check_momentum_flag(total_score: float | None, returns: dict[str, float | None]) -> dict:
    """total_score: calculate_total_score()'un "total_score" alanı.
    returns: yfinance_provider.fetch_price_returns() çıktısı ({"return_6m", "return_12m"}).

    Dönüş: {"flag": bool, "message": str}
    """
    return_6m = returns.get("return_6m")
    return_12m = returns.get("return_12m")

    if total_score is None or return_6m is None:
        return {
            "flag": False,
            "message": "momentum kontrolü yapılamadı: toplam skor veya 6 aylık getiri verisi yok",
        }

    is_weak = total_score > _TOTAL_SCORE_THRESHOLD and return_6m < _RETURN_6M_THRESHOLD

    return_12m_text = f"{return_12m:+.1f}%" if return_12m is not None else "yok"
    if is_weak:
        message = (
            f"MOMENTUM ZAYIF: toplam skor {total_score:.0f} (>{_TOTAL_SCORE_THRESHOLD:.0f}) "
            f"ama 6 aylık getiri {return_6m:+.1f}% (<{_RETURN_6M_THRESHOLD:.0f}%). "
            f"12 aylık getiri: {return_12m_text}. Skoru düşürmez, sadece bilgi amaçlıdır."
        )
    else:
        message = f"momentum normal: 6 aylık getiri {return_6m:+.1f}%, 12 aylık getiri {return_12m_text}"

    return {"flag": is_weak, "message": message}
