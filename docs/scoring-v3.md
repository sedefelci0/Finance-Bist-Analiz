# BIST Alpha Score v3 — Karar Belgesi (taslak)

Tarih: 12 Ekim 2026. Durum: tasarım kararları verildi, henüz uygulanmadı.
Bu belge Claude Code'un okuyup uygulaması için yazıldı. Belirsiz bir yer görürsen varsayım yapma, önce sor ve LEARNING.md'ye not düş.

## 1. Amaç

Skor şu soruya cevap verir: **"Bu şirket kaliteli mi, fiyatı makul mü, trendi bozuk değil mi?"**
Tahmin değildir, filtre ve özettir. Yatırım tavsiyesi değildir.

## 2. Verilen kararlar

1. **Kapsam:** Kalite + Güvenlik + Değerleme + Momentum.
2. **Şirket aileleri ayrı puanlanır.** Aile içinde, sektör karşılaştırma gruplarına göre yüzdelik hesaplanır.
3. **Büyüklük skordan çıkarıldı.** Piyasa değeri, likidite ve beta artık filtre/bilgi sütunudur.
4. **Borç ve nakit akışı Güvenlik pillar'ına girer.** Backlog (sipariş portföyü) Kalite pillar'ında opsiyonel, sınırlı ağırlıklı bir modüldür.
5. **Veri:** yfinance'te varsa ve para birimi uyuşuyorsa kullan, yoksa kendin hesapla (hibrit). Finansal tablolar için İş Yatırım tabanlı kaynak ana kaynak olarak değerlendirilecek (bkz. 12).
6. **Geçmişe dönük doğrulama (backtest) ilk sürümden sonraya bırakılabilir.** Ama bölüm 10'daki yayın kuralı zorunludur.

## 3. Aileler ve karşılaştırma grupları

**Aileler (hangi metrik seti uygulanır):**
1. Sanayi, ticaret, hizmet
2. Bankalar
3. Sigorta ve diğer finans (aracı kurum, faktoring vb.)
4. GYO
5. Holding ve yatırım şirketleri

**Karşılaştırma grupları (yüzdelik kiminle hesaplanır):**
- KAP ana sektör sınıflandırmasından türetilir. Her grupta **en az 8 hisse** olmalı. Küçük sektörleri yakın sektörlerle birleştir.
- Hâlâ 8'den küçükse aile geneliyle karşılaştır ve tabloda "geniş karşılaştırma" etiketi göster.
- Yüzdelik dilim **grup içinde** hesaplanır. Mutlak eşik kuralları (faiz karşılama < 1, işletme nakit akışı negatif gibi) gruptan bağımsız uygulanır.

## 4. Pillar'lar — Sanayi/ticaret/hizmet ailesi (ilk sürüm)

İlk taslak ağırlıklar (**test edilmemiş**, sonradan ayarlanacak): Kalite %30, Güvenlik %30, Değerleme %25, Momentum %15.

**Kalite (%30):** ROE, ROIC, faaliyet marjı, marj istikrarı (3 yıllık dalgalanma), reel gelir büyümesi (enflasyondan arındırılmış). Opsiyonel: Görünürlük (bölüm 8).

**Güvenlik (%30):** net borç / FAVÖK, faiz karşılama oranı (FAVÖK / faiz gideri), kısa vadeli borç payı, işletme nakit akışı / net kâr, serbest nakit akışı marjı, Piotroski F-Score (sadece 9 kriterin hepsi hesaplanabiliyorsa), Altman Z (sınırlı ağırlıkla, sanayi için).

**Değerleme (%25):** F/K, F/DD, FD/FAVÖK, serbest nakit akışı getirisi. PEG çoğu hissede eksik olduğu için kaldırıldı.

**Momentum (%15):** 12-1 aylık fiyat momentumu (son ay hariç), 6 aylık getiri, YoY marj değişimi (nötr gösterim: "marj YoY: −X puan", "bozulma/toparlanma" gibi yargılayıcı etiket yok).

**Eksik veri kuralı:** Eksik metrik 0 sayılmaz, ağırlığı pillar içinde yeniden dağıtılır. Bir pillar'ın metriklerinin %60'ından azı varsa o pillar "yetersiz veri" olur. İki ya da daha fazla pillar yetersizse toplam skor üretilmez.

## 5. Bankalar (Faz 2)

Kalite: ROE, ROA, net faiz marjı (varsa), maliyet/gelir oranı. Güvenlik: sermaye yeterlilik oranı, takipteki kredi oranı, kredi/mevduat, özkaynak/aktif. Değerleme: F/K, F/DD. Momentum: aynı.
Bu metriklerin verisi doğrulanmadı. Gelmeyen metrik "uygulanamaz" yazılır, uydurulmaz.

## 6. Diğer aileler (Faz 3, ilk sürümde "yakında")

- **Sigorta/aracı kurum:** ROE, özkaynak/aktif, F/K, F/DD. Marj ve Z-Score yok.
- **GYO:** faaliyet marjı yerine işletme nakit akışı (değerleme kazançları marjı şişiriyor). F/DD, net borç/özkaynak, faiz karşılama.
- **Holding:** konsolide rakamlar yanıltıcı. Ayrı grupta, skor yerine bilgi olarak göster.

## 7. Bilgi ve filtre sütunları (skora girmez)

Piyasa değeri, likidite (günlük işlem hacmi, halka açıklık), beta (BIST100'e göre, fiyat verisinden en az 120 işlem günüyle kendin hesapla), volatilite, net döviz pozisyonu (veri varsa), son bilanço dönemi, veri kapsamı, yüksek skor + düşen fiyat momentum uyarısı, YoY kâr değişimi (nötr).

## 8. Backlog / Görünürlük modülü (opsiyonel)

Neden: GLRMK gibi proje bazlı şirketlerde yıllık kâr geçmişe, backlog geleceğe bakar.

- **Elle girilir** (otomatik çekim kırılgan). Alanlar: backlog tutarı, para birimi, tarih, kaynak (KAP bildirimi veya faaliyet raporu bağlantısı), backlog / son 12 ay geliri oranı.
- **Sadece proje bazlı sektörler:** inşaat/taahhüt, savunma, gemi, ağır sanayi, enerji yatırımı.
- **Skora etkisi sınırlı:** Kalite pillar'ının en fazla %10'u. Oran (örneğin 0.5x altı 0, 3x üstü 100) eşikle puana çevrilir.
- **Veri yoksa metrik hesaba katılmaz** (eksik veri kuralı), tabloda "Backlog: girilmedi".
- **Veri 12 aydan eskiyse** hesaba katılmaz, "eski" etiketi.
- Skoru etkileyen elle girilmiş veri olduğu tabloda belirtilir: "(elle girilen veri içerir)".
- Dolaylı otomatik gösterge (bilgi alanı, skora girmez): müşteri avansları ve sözleşme yükümlülükleri değişimi, veri geliyorsa.

## 9. Kurallar

- **Para birimi:** tüm hesaplar TL. `financialCurrency != currency` ise o kaynaktan gelen çarpan kullanılmaz, fiyat ve tablolardan kendin hesapla.
- **Hibrit kural:** yfinance değeri sadece para birimi uyuşuyorsa ve makul aralıktaysa kullanılır. Her metriğin hangi kaynaktan geldiği kaydedilir.
- **Uç değer kırpma:** marj, ROE, ROIC [−100, +100]; cari oran üst sınır 10; Z-Score üst sınır 10. F/K ve diğer çarpanlarda negatif ya da anlamsız değerler "eksik" sayılır.
- **Tarihler:** bilanço dönemi, bilanço açıklanma tarihi (varsa) ve hesaplama tarihi ayrı alanlar.
- **Sürüm:** her kayıtta `score_version` ('v3'). v2 kayıtları silinmez.
- **Eski kayıt:** tabloda 7 günden eski kayıtlar gri ve "N gün önce" etiketiyle gösterilir, varsayılan görünümde gizlenebilir.
- **Tarama:** sonunda özet satırı (işlenen, yazılan, atlanan, hata). Hata oranı %20'yi aşarsa iş kırmızı biter. `set -o pipefail` kullan, log'u repoya commit'leme, artifact olarak yükle.
- **Evren:** resmi Borsa İstanbul CSV'si. Actions'ta erişilemezse sessizce eski listeye düşme, hata ver.
- **Şeffaflık:** her hissede hangi metrikler hesaplanabildi, hangileri hangi kaynaktan geldi görünür.

## 10. Yayın kuralı (v3 canlıya almadan önce)

1. Hisselerin en az %90'ı skorlanmış ya da nedeni yazılı "yetersiz veri".
2. Skor dağılımı mantıklı (min/max/ortalama), NaN yok.
3. Elle kontrol: en yüksek 10 ve en düşük 10 hisse, THYAO, TMSN, ASELS, GLRMK ve 2 banka.
4. 5 hissede en az 3 metriği (F/K, F/DD, net borç/FAVÖK) elle hesaplayıp karşılaştır.
5. Actions taraması baştan sona yeşil, özet log var.

Geçilmezse v2 canlıda kalır, v3 ayrı sürüm olarak beklemeye alınır. Geçmişe dönük doğrulama (yüksek skorlu hisseler sonraki aylarda piyasadan iyi gitti mi, bilanço açıklanma tarihlerine dikkat ederek) ilk sürümden sonraya bırakılır ve README'de "planlanan" olarak yazılır.

## 11. Aşamalar

| Aşama | Tarih | İçerik |
|---|---|---|
| Faz 0 | 12-13 Ekim | Veri kaynağı testi (20 hisse, İş Yatırım ↔ KAP ↔ yfinance), evren/Actions sorunu |
| Faz 1 | 14-18 Ekim | Yeni veri katmanı, sanayi/ticaret ailesi v3 (minimum çalışan sürüm), v3 ayrı sürüm olarak |
| Faz 2 | 19-25 Ekim | Bankalar, backlog modülü, Streamlit v3 görünümü, eski kayıt etiketleri |
| Faz 3 | 26-31 Ekim | Yayın kuralı kontrolü, README, güvenlik düzeltmeleri; GYO/sigorta/holding "yakında" |
| Sonra | Kasım+ | Geçmişe dönük doğrulama, ağırlık ayarı, kalan aileler |

Yetişmezse bırakma sırası: backlog → sigorta/GYO/holding → bankalar. Asla bırakılmayacaklar: çalışan ve tutarlı canlı site, README.

## 12. Açık sorular (Claude Code ile doğrula, varsayma)

- İş Yatırım'dan çeyreklik tablolar, nakit akışı kalemleri, faiz gideri ve banka metrikleri geliyor mu?
- Pay sayısı hangi kaynaktan alınacak?
- Karşılaştırma dönemleri TMS 29 bazında aynı bazda mı veriliyor? (YoY için kritik)
- GitHub Actions IP'lerinden İş Yatırım, KAP ve Borsa İstanbul CSV'sine erişim var mı?
- KAP sektör sınıflandırması için pykap mı kap-mcp mi uygun?
- Evren: ~290 hisse (resmi CSV) vs Actions'ta 149. Fark nereden geliyor?
- Kullanılan kaynakların kullanım koşulları ve istek sınırları.

## 13. Dayanaklar ve sınırlar (README'ye taşınacak)

**Tasarımın dayandığı çalışmalar:**
- Kalite ve Güvenlik: Asness, Frazzini, Pedersen, "Quality Minus Junk" (kalite = güvenli, kârlı, büyüyen). Piotroski (2000) F-Score: dokuz sinyalin hepsi hesaplanabiliyorsa kullanılır.
- Değerleme + Momentum birlikte: Asness, Moskowitz, Pedersen, "Value and Momentum Everywhere" (2013). İkisi negatif korelasyonlu, birleşimi tek başına birinden daha iyi. Momentum, değer tuzağına karşı fren görevi görür.
- Borsa İstanbul: Özer & Yıldırım Kutbay (2022), Uludağ tezi (kârlılık ve momentum etkileri), Özyeğin "Mispricing in Borsa Istanbul".

**Dürüst sınırlar (README'de açıkça yazılacak):**
- **Ağırlıklar (%30/30/25/15) bu projenin kendi tasarımıdır, test edilmemiştir.** Özer & Yıldırım Kutbay özetinde doğrudan ağırlık önerisi görülmedi. Tam metin doğrulanana kadar "makaleye dayanıyor" ifadesi kullanılmaz, "literatürden esinlenilmiştir" denir.
- **Bankalar:** BIST faktör çalışmalarının çoğu mali şirketleri hariç tutuyor. Bankaları ayrı aile olarak puanlıyoruz, akademik dayanağı sınırlı.
- **Büyüklük:** Skordan çıkarıldı (filtre/bilgi). "Size Matters If You Control Your Junk" küçüklük priminin kalite kontrol edilince ortaya çıktığını söylüyor, bu karar doğrulama aşamasında yeniden test edilecek.
- **Reel büyüme / varlık büyümesi:** BIST'te varlık büyümesi anomalisi ABD'ye göre ters yönde çalışıyor. Test edilene kadar küçük ağırlıklı ya da bilgi sütunu olarak tut.
- **Skor tahmin değildir.** Geçmiş bilançoya dayanan bir kalite ve değerleme özetidir. Yatırım tavsiyesi değildir.
