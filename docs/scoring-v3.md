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
5. **Veri (Faz 0 sonrası, 13 Ekim):** Finansal tablolar **hisse bazında tek kaynaktan** gelir; kalem kalem karıştırma yok (bkz. bölüm 9 "Veri kaynağı"). Fiyat verisi yfinance'ten (araştırma/eğitim amaçlı) ayrı ve sık çekilir. Sitede yalnızca türetilmiş skorlar gösterilir; ham tablo ve fiyat serisi gösterilmez, ham sağlayıcı verisi repoya girmez.
6. **Geçmişe dönük doğrulama (backtest) ilk sürümden sonraya bırakılabilir.** Ama bölüm 10'daki yayın kuralı zorunludur.

## 3. Aileler ve karşılaştırma grupları

**Aileler (hangi metrik seti uygulanır):**
1. Sanayi, ticaret, hizmet
2. Bankalar
3. Sigorta ve diğer finans (aracı kurum, faktoring vb.)
4. GYO
5. Holding ve yatırım şirketleri

**Karşılaştırma grupları (yüzdelik kiminle hesaplanır):**
- KAP **alt sektör** sınıflandırmasından türetilir (ana sektör yetmez: KAP'ta holding, GYO, aracı kurum, sigorta ve banka hepsi "MALİ KURULUŞLAR" ana sektöründe). Aile ataması alt sektör + tablo formatı (sanayi `XI_29` / banka / sigorta) ile yapılır; istisnalar elle düzeltme listesinde tutulur (örn. SISE KAP'ta "Holdingler ve Yatırım Şirketleri" altında). Her grupta **en az 8 hisse** olmalı. Küçük sektörleri yakın sektörlerle birleştir.
- Hâlâ 8'den küçükse aile geneliyle karşılaştır ve tabloda "geniş karşılaştırma" etiketi göster.
- Yüzdelik dilim **grup içinde** hesaplanır. Mutlak eşik kuralları (faiz karşılama < 1, işletme nakit akışı negatif gibi) gruptan bağımsız uygulanır.

## 4. Pillar'lar — Sanayi/ticaret/hizmet ailesi (ilk sürüm)

İlk taslak ağırlıklar (**test edilmemiş**, sonradan ayarlanacak): Kalite %30, Güvenlik %30, Değerleme %25, Momentum %15.

**Kalite (%30):** ROE, ROIC, faaliyet marjı, marj istikrarı (3 yıllık dalgalanma), reel gelir büyümesi (enflasyondan arındırılmış). Opsiyonel: Görünürlük (bölüm 8).

**Güvenlik (%30):** net borç / FAVÖK, faiz karşılama oranı (FAVÖK / faiz gideri), kısa vadeli borç payı, işletme nakit akışı / net kâr, serbest nakit akışı marjı, Piotroski F-Score (sadece 9 kriterin hepsi hesaplanabiliyorsa), Altman Z (sınırlı ağırlıkla, sanayi için).

**Değerleme (%25):** F/K, F/DD, FD/FAVÖK, serbest nakit akışı getirisi. PEG çoğu hissede eksik olduğu için kaldırıldı.

**Momentum (%15):** 12-1 aylık fiyat momentumu (son ay hariç), 6 aylık getiri, YoY marj değişimi (nötr gösterim: "marj YoY: −X puan", "bozulma/toparlanma" gibi yargılayıcı etiket yok).

**Eksik veri kuralı:** Eksik metrik 0 sayılmaz, ağırlığı pillar içinde yeniden dağıtılır. Bir pillar'ın metriklerinin %60'ından azı varsa o pillar "yetersiz veri" olur. İki ya da daha fazla pillar yetersizse toplam skor üretilmez.

**Kalem tanımları (yalnızca sanayi/ticaret/hizmet ailesi, İş Yatırım kaynaklı; 13 Ekim kullanıcı onayı):**
- **EBIT = "FAALİYET KARI (ZARARI)"** (İş Yatırım kodu `3DF`). Şirketin KAP'taki "ESAS FAALİYET KARI (ZARARI)" satırıyla aynıdır (ASELS 2026/6: 22.530.965 bin TL, birebir). Kapsam: Brüt Kar (Zarar) − Pazarlama, Satış ve Dağıtım Giderleri − Genel Yönetim Giderleri − Araştırma ve Geliştirme Giderleri + Diğer Faaliyet Gelirleri − Diğer Faaliyet Giderleri. **Hariç:** Yatırım Faaliyetlerinden Gelirler/Giderler, Özkaynak Yöntemiyle Değerlenen Yatırımların Kar/Zararlarındaki Paylar, Finansman Gelirleri/Giderleri ve **TMS 29 "Net Parasal Pozisyon Kazançları (Kayıpları)"** (ASELS 2026/6 KAP raporunda finansman giderlerinden sonra, vergi öncesi kârdan önce ayrı satır). "Finansman Gideri Öncesi Faaliyet Karı/Zararı" (`3HACA`) yatırım faaliyeti ve özkaynak yöntemi paylarını içerdiği için **kullanılmaz**.
- **Geçmiş yıllar kârı (Altman B) = "Geçmiş Yıllar Kar/Zararları" + "Kardan Ayrılan Kısıtlanmış Yedekler"** (`2OCE` + `2OCD`). Kâr yedekleri (kısıtlanmış yedekler) **dahil**, "Dönem Net Kar/Zararı" (`2OCF`) **hariç**.
- yfinance'in "EBIT" ve "Retained Earnings" satırları bu tanımlarla eşleşmez (ASELS 2024: yfinance EBIT 16,6 mlr, esas faaliyet kârı 35,8 mlr; yfinance geçmiş yıllar kârı 108,3 mlr, yukarıdaki tanım 94,9 mlr). Aynı metrik iki kaynakta farklı tanımla hesaplanırsa yüzdelikler karışır → hisse bazında tek kaynak kuralı (bölüm 9) bu yüzden zorunludur.
- Bankalarda Z-Score uygulanmaz; sigorta için tanım ayrıca yapılacak.

**TMS 29 / dönem birimi kuralı:** Aynı hesapta kullanılan tüm rakamlar aynı satın alma gücü biriminde olmalı. Kaynaklar eski dönemleri farklı tarihlerin TL'si ile verir (Faz 0: İş Yatırım 2025/12'yi Haziran 2026 TL'si ile, yfinance Aralık 2025 TL'si ile veriyor, fark ×1,1776). YoY, reel büyüme ve marj istikrarı aynı raporun cari ve karşılaştırmalı sütunlarından hesaplanır; her kayıtta dönemin hangi tarihin birimiyle ifade edildiği saklanır. Kümülatif çeyreklerden tekil çeyrek türetirken iki sütun aynı birimde değilse türetme yapılmaz.
Faz 0'da kanıtlanan birimler (2026/6 itibarıyla): ×1,1776 = TÜFE(Haziran 2026) / TÜFE(Aralık 2025). İş Yatırım: 2026/6, 2025/12 ve 2025/6 **Haziran 2026 TL'si** (2025/6, KAP'taki 2026/6 raporunun karşılaştırmalı sütunuyla birebir), 2026/3 **Mart 2026 TL'si**. yfinance: 2025/12 yıllık **Aralık 2025 TL'si**; 2026Ç2 ve 2025Ç2 çeyrekleri şirketin 3 aylık sütunu (Haziran 2026 TL'si). Yani iki kaynakta da tek bir cevabın sütunları aynı birimde değildir.

**TTM kuralı:** İş Yatırım kaynaklı hissede TTM = Yıl(Y−1) + Kümülatif(Y) − Kümülatif(Y−1, aynı ay). En güncel dönemde bu üç sütun aynı birimdedir (Faz 0: 2025/12, 2026/6, 2025/6 → Haziran 2026 TL'si). Tekil çeyrekler toplanarak TTM hesaplanmaz. yfinance kaynaklı hissede TTM son 4 çeyreğin hepsi doluysa hesaplanır; bir çeyrek eksikse (Faz 0: 20 hissenin 7'sinde 2025Ç3 gelir tablosu yok) TTM "veri yok", kalem başka kaynaktan tamamlanmaz.

## 5. Bankalar (Faz 2)

Kalite: ROE, ROA, net faiz marjı (varsa), maliyet/gelir oranı. Güvenlik: sermaye yeterlilik oranı, takipteki kredi oranı, kredi/mevduat, özkaynak/aktif. Değerleme: F/K, F/DD. Momentum: aynı.
Faz 0'da doğrulandı: İş Yatırım `UFRS_K` (konsolide) tablosu kullanılır, `UFRS` solo tablodur. Faiz gelir/gider, kredi, mevduat, özkaynak, aktif var → net faiz marjı, kredi/mevduat, özkaynak/aktif, ROE, ROA hesaplanabilir. **Sermaye yeterlilik oranı ve takipteki kredi oranı kaynaklarda yok** (takipteki krediler alanı 0 geliyor) → ilk sürümde "uygulanamaz". Banka ve sigorta tablolarında nakit akışı bölümü yok. Gelmeyen metrik "uygulanamaz" yazılır, uydurulmaz.

## 6. Diğer aileler (Faz 3, ilk sürümde "yakında")

- **Sigorta/aracı kurum:** ROE, özkaynak/aktif, F/K, F/DD. Marj ve Z-Score yok.
- **GYO:** faaliyet marjı yerine işletme nakit akışı (değerleme kazançları marjı şişiriyor). F/DD, net borç/özkaynak, faiz karşılama.
- **Holding:** konsolide rakamlar yanıltıcı. Ayrı grupta, skor yerine bilgi olarak göster.

## 7. Bilgi ve filtre sütunları (skora girmez)

Bu sütunlar türetilmiş değer olarak gösterilir (ör. "beta 1,2", "likidite: yüksek"); ham fiyat serisi ya da ham tablo gösterilmez.

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
- **Veri kaynağı (hisse bazında tek kaynak):** Bir şirketin finansal tablolarının tamamı ya yfinance'ten ya İş Yatırım'dan gelir; kalem kalem karıştırma yok. Önce yfinance: **"tam"** ise kullanılır, değilse (eksik dönem, USD raporlama — örn. THYAO, ENKAI) tüm set İş Yatırım'dan alınır. **"Tam" tanımı:** son 5 çeyrek + son yıllık dönem (+ F-Score için bir önceki yıllık) mevcut; `financialCurrency == TRY`; gerekli kalemler dolu (ROE, ROIC, marjlar, net borç/FAVÖK, faiz karşılama, işletme nakit akışı, F-Score'un 9 girdisi); en güncel dönem beklenen dönemden eski değil; bilanço özdeşliği (varlık = yükümlülük + özkaynak, %1 tolerans) ve makul aralık kontrolleri geçiyor.
  **KESİNLEŞMEDİ (13 Ekim):** Faz 0 sayımında 16 sanayi hissesinden yalnızca **6'sı** "tam" geçti (EKGYO, KCHOL, SISE, TMSN, TUPRS, ULKER). Bu kontrol yfinance'in yanlış etiketli çeyreklerini de yakalamıyor (ASELS 2026Ç2 = önceki yılın 6 aylık rakamı). **Öneri: tüm finansal tablolar için İş Yatırım tek ana kaynak; yfinance yalnızca fiyat için.** Karar kullanıcıda. Her kayıtta kaynak, para birimi ve birim (TMS 29 tarihi) saklanır.
- **Çekme sıklığı:** İş Yatırım yavaş (Faz 0: 20 hissede 17–31 zaman aşımı). Tablo bir kez çekilir, ham hâliyle Neon'da saklanır, yalnızca yeni bilanço açıklanınca yeniden çekilir. İş Yatırım uç noktası en az 4 dönem istenmezse boş liste döner; "0 kalem" hata sayılır. Fiyat ayrı ve sık çekilir.
- **Gösterim:** sitede yalnızca türetilmiş skorlar ve oranlar; ham tablo ve fiyat serisi gösterilmez, repoya da girmez.
- **Uç değer kırpma:** marj, ROE, ROIC [−100, +100]; cari oran üst sınır 10; Z-Score üst sınır 10. F/K ve diğer çarpanlarda negatif ya da anlamsız değerler "eksik" sayılır.
- **Tarihler:** bilanço dönemi, bilanço açıklanma tarihi (varsa) ve hesaplama tarihi ayrı alanlar.
- **Sürüm:** her kayıtta `score_version` ('v3'). v2 kayıtları silinmez.
- **Eski kayıt:** tabloda 7 günden eski kayıtlar gri ve "N gün önce" etiketiyle gösterilir, varsayılan görünümde gizlenebilir.
- **Tarama:** sonunda özet satırı (işlenen, yazılan, atlanan, hata). Hata oranı %20'yi aşarsa iş kırmızı biter. `set -o pipefail` kullan (Faz 0: mevcut `scan.yml`'de yok, 14 Ağustos–10 Ekim arası ~24 koşu DB'ye hiç yazmadan yeşil bitti), log'u repoya commit'leme, artifact olarak yükle. DB'ye yazılan kayıt sayısı 0 ise iş kırmızı biter.
- **Evren:** resmi Borsa İstanbul CSV'si. Actions'ta erişilemezse sessizce eski listeye düşme, hata ver. **Dikkat (Faz 0):** CSV'deki `XYLDZ` endeks kodu Yıldız Pazar'ın tamamı değil (bugün 149 hisse; Temmuz 2026'da Yıldız Pazar'a geçen CGCAM, MERIT, NETCD, YATAS XYLDZ'de yok). **Karar (13 Ekim): evren `XYLDZ`.** Endeks kodu kodda sabit değil, ayardır (genişletmek tek satır + daha uzun ilk dolum). Gerekçe: İş Yatırım yavaş, XUTUM (582) ilk dolumu günler sürer ve çok sayıda işlem görmeyen hisse boş veri sorununu artırır. 149 hisselik evrende "en az 8 hisse" kuralı küçük sektör gruplarının birleştirilmesini gerektirir (bölüm 3). Sitedeki ~290 hisse: v2 sitesi her hissenin **en son koşusunu ne kadar eski olursa olsun** gösteriyor (`app.py` `load_latest_pillar_scores`), bu yüzden Ağustos'taki 270–288 hisselik taramalardan kalan, evrende artık olmayan hisseler de listeleniyor. v3'te evren dışı hisseler gösterilmez.
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
| Faz 0 | 12-13 Ekim | Veri kaynağı testi (20 hisse, İş Yatırım ↔ KAP ↔ yfinance), evren/Actions sorunu — **tamamlandı (13 Ekim), bkz. `docs/faz0/faz0-raporu.md`** |
| Faz 1 | 14-18 Ekim | Yeni veri katmanı, sanayi/ticaret ailesi v3 (minimum çalışan sürüm), v3 ayrı sürüm olarak |
| Faz 2 | 19-25 Ekim | Bankalar, backlog modülü, Streamlit v3 görünümü, eski kayıt etiketleri |
| Faz 3 | 26-31 Ekim | Yayın kuralı kontrolü, README, güvenlik düzeltmeleri; GYO/sigorta/holding "yakında" |
| Sonra | Kasım+ | Geçmişe dönük doğrulama, ağırlık ayarı, kalan aileler |

Yetişmezse bırakma sırası: backlog → sigorta/GYO/holding → bankalar. Asla bırakılmayacaklar: çalışan ve tutarlı canlı site, README.

## 12. Açık sorular (Claude Code ile doğrula, varsayma)

> Faz 0'da cevaplandı: `docs/faz0/faz0-raporu.md` bölüm 5. Açık kalan: ana finansal kaynak yfinance mı İş Yatırım mı (bölüm 9, KESİNLEŞMEDİ); KAP verisinin kullanım koşulları; sigorta ailesinin kalem tanımları.

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
- **Veri kaynakları ve koşulları:** yfinance ve İş Yatırım'ın kendi metinleri ve `robots.txt` dosyaları README'de aynen aktarılır (bkz. `docs/readme-taslak.md`). Sitede yalnızca türetilmiş skorlar gösterilir.
- **TMS 29:** kaynaklar eski dönemleri farklı tarihlerin TL'si ile verir; büyüme ve YoY bu yüzden kaynağa duyarlıdır.
- **Skor tahmin değildir.** Geçmiş bilançoya dayanan bir kalite ve değerleme özetidir. Yatırım tavsiyesi değildir.
