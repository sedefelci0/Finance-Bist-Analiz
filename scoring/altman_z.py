"""Altman Z-Score (orijinal, halka açık/imalat şirketleri formülü).

Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
  A = İşletme Sermayesi (Dönen Varlıklar - KV Yükümlülükler) / Toplam Varlıklar
  B = Geçmiş Yıllar Kârları / Toplam Varlıklar
  C = EBIT / Toplam Varlıklar
  D = Piyasa Değeri (Özkaynak) / Toplam Yükümlülükler
  E = Satışlar (Hasılat) / Toplam Varlıklar

Sınıflandırma: Z > 2.99 Güvenli, 1.81 <= Z <= 2.99 Gri Bölge, Z < 1.81 Sıkıntılı.

Kaynak: Altman, E. (1968), "Financial Ratios, Discriminant Analysis and the
Prediction of Corporate Bankruptcy".

NOT: B bileşeni (retained_earnings) KAP'ın özet finansal tablo sayfasında
bulunmuyor — sadece yfinance'ten gelir (bkz. providers/kap_provider.py).
financialCurrency USD olan (dolayısıyla yfinance'i tamamen reddedilen)
tickerlarda bu bileşen hep eksik olacak ve Z-Score TAMAMEN hesaplanamayacak
("veri yok" olarak işaretlenir) — kısmi/yanıltıcı bir Z-Score üretmemek için
5 bileşenden biri bile eksikse tüm skor None döner.
"""
from __future__ import annotations

Metrics = dict[str, float | None]


def calculate_altman_z(metrics: Metrics, market_cap: float | None) -> dict:
    """metrics: normalizer'ın döndürdüğü tek bir dönemin kalemleri.
    market_cap: yfinance_provider.fetch_market_data()'dan (anlık, dönemsel değil).

    Dönüş: {"z_score": float | None, "zone": str | None, "notes": str,
            "components": {"A":..., "B":..., "C":..., "D":..., "E":...} | None}
    """
    total_assets = metrics.get("total_assets")
    current_assets = metrics.get("current_assets")
    current_liabilities = metrics.get("current_liabilities")
    retained_earnings = metrics.get("retained_earnings")
    ebit = metrics.get("ebit")
    total_liabilities = metrics.get("total_liabilities")
    revenue = metrics.get("revenue")

    missing = []
    if total_assets is None or total_assets == 0:
        missing.append("total_assets")
    if current_assets is None:
        missing.append("current_assets")
    if current_liabilities is None:
        missing.append("current_liabilities")
    if retained_earnings is None:
        missing.append("retained_earnings")
    if ebit is None:
        missing.append("ebit")
    if market_cap is None:
        missing.append("market_cap")
    if total_liabilities is None or total_liabilities == 0:
        missing.append("total_liabilities")
    if revenue is None:
        missing.append("revenue")

    if missing:
        return {
            "z_score": None,
            "zone": None,
            "notes": f"veri yok: {', '.join(missing)} eksik olduğu için Z-Score hesaplanamadı",
            "components": None,
        }

    a = (current_assets - current_liabilities) / total_assets
    b = retained_earnings / total_assets
    c = ebit / total_assets
    d = market_cap / total_liabilities
    e = revenue / total_assets

    z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e

    if z > 2.99:
        zone = "güvenli"
    elif z >= 1.81:
        zone = "gri"
    else:
        zone = "sıkıntılı"

    components = {"A": a, "B": b, "C": c, "D": d, "E": e}
    notes = (
        f"Z={z:.2f} ({zone}) — A(işletme sermayesi/aktif)={a:.2f}, "
        f"B(geçmiş yıl kârları/aktif)={b:.2f}, C(EBIT/aktif)={c:.2f}, "
        f"D(piyasa değeri/yükümlülük)={d:.2f}, E(hasılat/aktif)={e:.2f}"
    )

    return {"z_score": z, "zone": zone, "notes": notes, "components": components}
