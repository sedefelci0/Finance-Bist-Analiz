# İş Yatırım ↔ KAP karşılaştırması (Faz 0, adım 2)

Tarih: 12 Ekim 2026. Ham tablo: `kap_vs_isyatirim.csv`.

- **KAP tarafı:** `kap.org.tr/tr/sirket-finansal-bilgileri/<slug>` özet sayfası, projedeki
  `providers/kap_provider.py` ile (Playwright) okundu. Bu sayfa her dönemi **ilk yayımlandığı haliyle** gösteriyor.
- **İş Yatırım tarafı:** `MaliTablo` uç noktası, sanayi için `XI_29`, banka için `UFRS_K` (konsolide).

## Sonuç

| Hisse | 2026/6 | 2025/12 | 2024/12 | 2023/12 |
|---|---|---|---|---|
| THYAO | aynı | İş = KAP × 1,1776 | İş = KAP × 1,3089 | aynı (≤%0,1) |
| ASELS | aynı | × 1,1776 | × 1,3089 | × 1,4438 |
| GLRMK | aynı | × 1,1776 | × 1,3089 | KAP'ta dönem yok |
| TMSN | aynı | × 1,1776 | × 1,3089 | × 1,44 (kalemlere göre 1,35–1,44) |
| GARAN (net kâr) | KAP sayfası 1000 kat küçük okundu* | aynı | aynı | aynı |

"Aynı" = toplam varlık, satış, net kâr ve ana ortaklık özkaynağında fark < %0,6.
Kalan küçük farklar **tanım** farkıdır: KAP sayfasının "Net Dönem Karı" toplam kârdır, İş'in `3Z`'si
ana ortaklık payıdır; KAP'ın özkaynağı ana ortaklığa aittir, İş'in `2N`'si azınlık dahil toplamdır.

## Farkın nedeni: TMS 29 yeniden ifadesi (kanıtlı)

Katsayılar şirketten bağımsız ve TÜFE ile birebir örtüşüyor (TCMB TÜFE serisi, borsapy üzerinden):

| Katsayı | TÜFE karşılığı |
|---|---|
| 1,1776 | Ocak–Haziran 2026 aylık TÜFE çarpımı = 1,1775 |
| 1,3089 | 2025 yıllık TÜFE %30,89 |
| 1,4438 | 2024 yıllık TÜFE %44,38 |

Yorum: İş Yatırım her dönemi, o dönemi **karşılaştırmalı sütun olarak veren bir sonraki raporun**
yeniden ifade edilmiş rakamıyla gösteriyor. Bu nedenle tek bir İş Yatırım cevabındaki sütunlar
**farklı satın alma gücü bazındadır**: 2025/12 Haziran 2026 TL'si, 2024/12 Aralık 2025 TL'si, 2023/12 Aralık 2024 TL'si.
KAP özet sayfası ise her dönemi kendi tarihindeki TL ile gösteriyor.

Bankalarda fark yok (GARAN 2023–2025 net kâr birebir): bankalar TMS 29 uygulamıyor.

## Doğrulanamayanlar

- **THYAO 2023/12'nin KAP ile aynı olması** (diğer şirketlerde ×1,44). THY'nin geçerli para birimi USD;
  2024 ve 2025 sütunlarında yine TÜFE katsayısı görünüyor. Neden 2023'te görünmediği doğrulanamadı.
- **\*GARAN 2026/6 net kâr:** KAP sayfasından 64,4 **milyon**, İş'ten 64,4 **milyar** okundu. Önceki yıllar birebir.
  Bu büyük ihtimalle KAP sayfasındaki "Sunum Para Birimi" satırının banka formatında farklı olması ve
  `kap_provider.py`'nin çarpanı yanlış okuması. Ayrıca bankada toplam varlık ve özkaynak etiketleri eşleşmedi (NaN).
  Elle doğrulama yapılmadı.
- Ara dönemler (2025/6, 2026/3): KAP özet sayfasında bu sütunlar yok, karşılaştırılamadı.

## Skor için anlamı

- YoY karşılaştırmada (2026/6 ↔ 2025/6) iki sütunun aynı bazda olup olmadığı ayrıca kontrol edilmeli.
  İş'in 2025/6 rakamları yuvarlak (bin TL), bu da 2026/6 raporunun karşılaştırmalı sütunundan geldiğini düşündürüyor; **doğrulanmadı**.
- İş Yatırım kümülatif çeyrekten tekil çeyrek türetmek **hatalı sonuç verir**, çünkü 2025/9 ve 2025/12 farklı bazda
  (THYAO 2025Ç4 satışı 434 mlr çıkıyor, Ç3 283 mlr; USD bazında Ç4 Ç3'ten küçük).
- Marj ve ROE gibi aynı dönemin oranları bundan etkilenmez; büyüme ve YoY metrikleri etkilenir.
