"""TMS 29: tutarları tek bir TL bazına (satın alma gücü tarihine) çevirme ve kümülatif TTM.

TÜFE kaynağı (kullanıcı kararı, 13 Ekim): elle doldurulan, versiyonlu CSV
(`data/tufe/tufe_v<N>.csv`; sütunlar: ay, endeks, kaynak). Paket/servis yok.

Bir tutarın hangi tarihin TL'si ile ifade edildiği ("birim tarihi") bu modülde
TAHMİN EDİLMEZ, çağıran taraf açıkça verir. Faz 0'da yalnızca ASELS ile
kanıtlanan birim kuralı 10 hissede doğrulanmadan otomatikleştirilmeyecek
(bkz. LEARNING.md). TMS 29 uygulamayan şirketlerde (bankalar, USD işlevsel
para birimliler) çağıran taraf `apply_tms29=False` verir.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

Month = tuple[int, int]


class MissingCPIError(KeyError):
    """İstenen ay TÜFE dosyasında yok — sessizce tahmin edilmez."""


def load_cpi(path: str | Path) -> dict[Month, float]:
    """`ay` (YYYY-MM), `endeks`, `kaynak` sütunlu CSV'yi okur. Kaynak alanı boş satır kabul edilmez."""
    cpi: dict[Month, float] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("kaynak", "").strip():
                raise ValueError(f"TÜFE satırında kaynak bağlantısı yok: {row}")
            y, m = (int(x) for x in row["ay"].strip().split("-"))
            if (y, m) in cpi:
                raise ValueError(f"TÜFE dosyasında tekrar eden ay: {row['ay']}")
            cpi[(y, m)] = float(row["endeks"])
    return cpi


def cpi_factor(unit_date: date, base_date: date, cpi: dict[Month, float]) -> float:
    """TÜFE(baz) / TÜFE(birim). Ay sonu tarihleri ay bazında eşlenir."""
    try:
        return cpi[(base_date.year, base_date.month)] / cpi[(unit_date.year, unit_date.month)]
    except KeyError as exc:
        raise MissingCPIError(f"TÜFE ayı eksik: {exc.args[0]}") from None


def to_base(
    value: float | None,
    unit_date: date,
    base_date: date,
    cpi: dict[Month, float],
    *,
    apply_tms29: bool = True,
) -> float | None:
    """`unit_date` TL'si ile ifade edilmiş tutarı `base_date` TL'sine çevirir."""
    if value is None:
        return None
    if not apply_tms29 or unit_date == base_date:
        return value
    return value * cpi_factor(unit_date, base_date, cpi)


def ttm_cumulative(
    annual_prev: float | None,
    cum_current: float | None,
    cum_prev_same_month: float | None,
    month: int,
) -> float | None:
    """TTM(Y, ay) = Yıl(Y−1) + Kümülatif(Y, ay) − Kümülatif(Y−1, ay).

    Üç tutar ÖNCEDEN aynı TL bazına çevrilmiş olmalı (bkz. `to_base`).
    Ay 12 ise TTM = Kümülatif(Y, 12) = Yıl(Y). Eksik parça varsa None — tahmin yok.
    """
    if month == 12:
        return cum_current
    if annual_prev is None or cum_current is None or cum_prev_same_month is None:
        return None
    return annual_prev + cum_current - cum_prev_same_month
