"""Piotroski F-Score'un 9 kriteri için görüntüleme metadata'sı (etiket, kategori,
statik tanım). Sadece SUNUM amaçlı — hesaplama mantığı scoring/piotroski.py'de.

Ayrı bir dosyada tutuluyor ki ileride metinler (örn. daha iyi bir "neden"
açıklaması) hesaplama koduna dokunmadan güncellenebilsin.

Klasik Piotroski gruplaması (literatürdeki orijinal 3 kategori):
  Kârlılık (Profitability)              — 4 kriter
  Kaldıraç / Likidite (Leverage/Liquidity) — 3 kriter
  Operasyonel Verimlilik (Operating Efficiency) — 2 kriter
"""
from __future__ import annotations

CATEGORIES: dict[str, dict[str, str]] = {
    "profitability": {"label": "Kârlılık", "order": 1},
    "leverage_liquidity": {"label": "Kaldıraç / Likidite", "order": 2},
    "operating_efficiency": {"label": "Operasyonel Verimlilik", "order": 3},
}

# criterion_key -> {label, category, description}
# description: kriterin GENEL (şirketten bağımsız) tanımı — dinamik sonuçla
# (notes) birleştirilerek app.py'de "neden bu puan?" açıklaması oluşturuluyor.
CRITERIA_INFO: dict[str, dict[str, str]] = {
    "net_kar_pozitif": {
        "label": "Net Kâr Pozitif",
        "category": "profitability",
        "description": (
            "Şirket bu dönemde kâr mı etti, zarar mı? En temel kârlılık testi — "
            "net kâr sıfırın üzerindeyse 1 puan."
        ),
    },
    "faaliyet_nakit_akisi_pozitif": {
        "label": "Faaliyet Nakit Akışı Pozitif",
        "category": "profitability",
        "description": (
            "Esas iş faaliyetlerinden GERÇEKTEN nakit girişi var mı? Kâr muhasebesel "
            "olabilir (henüz tahsil edilmemiş satışlar gibi) — bu kriter nakdin "
            "gerçekten girip girmediğine bakar."
        ),
    },
    "roa_degisimi": {
        "label": "ROA (Aktif Kârlılığı) Arttı mı?",
        "category": "profitability",
        "description": (
            "ROA = Net Kâr ÷ Toplam Varlıklar. Şirket, sahip olduğu varlıklarla geçen "
            "yıla göre daha mı verimli kâr üretiyor?"
        ),
    },
    "nakit_akisi_net_kardan_buyuk": {
        "label": "Nakit Akışı Kalitesi (CFO > Net Kâr)",
        "category": "profitability",
        "description": (
            "Faaliyet nakit akışı, muhasebesel net kârdan büyük mü? Büyükse kârın "
            "\"kalitesi\" yüksek sayılır — kâr sadece kağıt üzerinde değil, nakde "
            "dönüşüyor demektir."
        ),
    },
    "uzun_vadeli_borc_azalisi": {
        "label": "Uzun Vadeli Borç/Aktif Azaldı mı?",
        "category": "leverage_liquidity",
        "description": (
            "Şirket, toplam varlıklarına oranla daha AZ uzun vadeli borç mu "
            "kullanıyor? Kaldıraç (borçluluk) azalması finansal risk azalması "
            "anlamına gelir."
        ),
    },
    "cari_oran_iyilesmesi": {
        "label": "Cari Oran İyileşti mi?",
        "category": "leverage_liquidity",
        "description": (
            "Cari Oran = Dönen Varlıklar ÷ Kısa Vadeli Yükümlülükler. Şirketin "
            "kısa vadeli borçlarını ödeme gücü (likidite) geçen yıla göre "
            "iyileşti mi?"
        ),
    },
    "hisse_sayisi_sulanmadi": {
        "label": "Hisse Sayısı Seyrelmedi mi?",
        "category": "leverage_liquidity",
        "description": (
            "Şirket yeni hisse ihraç ederek mevcut ortakları \"seyreltti\" mi? "
            "Hisse sayısı artmadıysa (ya da azaldıysa) bu, şirketin sermaye "
            "artırımına ihtiyaç duymadığının bir işareti sayılır."
        ),
    },
    "brut_kar_marji_iyilesmesi": {
        "label": "Brüt Kâr Marjı Arttı mı?",
        "category": "operating_efficiency",
        "description": (
            "Brüt Kâr Marjı = Brüt Kâr ÷ Hasılat. Şirket, sattığı ürün/hizmet "
            "başına geçen yıla göre daha mı fazla kâr bırakıyor (maliyet "
            "kontrolü/fiyatlama gücü)?"
        ),
    },
    "aktif_devir_hizi_iyilesmesi": {
        "label": "Aktif Devir Hızı Arttı mı?",
        "category": "operating_efficiency",
        "description": (
            "Aktif Devir Hızı = Hasılat ÷ Toplam Varlıklar. Şirket, sahip olduğu "
            "varlıklarla geçen yıla göre daha mı fazla satış üretiyor "
            "(operasyonel verimlilik)?"
        ),
    },
}


def build_why_explanation(criterion_key: str, notes: str, score: int | None) -> str:
    """Statik tanım + kriterin somut (dinamik) sonucunu birleştirip 'neden bu
    puan?' açıklaması üretir. Sabit bir şablon string'i — LLM ÇAĞRISI YOK.
    """
    info = CRITERIA_INFO.get(criterion_key, {"description": ""})
    description = info.get("description", "")
    if score is None:
        verdict = "Bu şirket için hesaplanamadı (veri eksik)."
    elif score == 1:
        verdict = f"Bu şirket için SAĞLANDI ✅ — {notes}"
    else:
        verdict = f"Bu şirket için SAĞLANMADI ❌ — {notes}"
    return f"{description}\n\n**Bu şirkette:** {verdict}"
