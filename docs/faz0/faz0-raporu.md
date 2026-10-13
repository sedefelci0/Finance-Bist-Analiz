# Faz 0 Raporu — Veri kaynakları ve evren

Tarih: 12 Ekim 2026 (Actions sonuçları 13 Ekim'de eklendi). Karar belgesi: `docs/scoring-v3.md`. Adım adım gerekçeler: `LEARNING.md`.

> **Durum:** Faz 0'ın 6 adımı tamamlandı. 20 hisselik tablo (1.3) Actions koşusundan
> (run 38264568323, aynı script) alındı; yereldeki ikinci tam koşu oturum kapanınca 17/20'de
> kesildi ve tekrarlanmadı (aynı test bulutta tamamlandığı için). Açık kalan sorular bölüm 5 ve devir notunda.

---

## 0. Kullanıcı kararları (bu oturumda)

1. **Site herkese açık olacak, yalnızca yasal kaynak kullanılacak.**
2. **Fiyat verisi için ücretsiz olanı seçiyoruz** (ücretli lisans yok).
3. Araştırma koşusu (İş Yatırım + Yahoo) bitsin, bulguları rapora girsin.
4. Test script'i ve workflow'u `faz0-veri-testi` dalına push edildi (onaylı).

Bu kararlar belgedeki "yfinance + İş Yatırım hibrit" yaklaşımını geçersiz kılıyor (bkz. bölüm 6).

---

## 1. Veri kaynağı testi

**Script:** `scripts/faz0_source_test.py` (aynı script yerelde ve Actions'ta). 20 hisse:
THYAO, ASELS, TMSN, GLRMK, GARAN, AKBNK, AGESA, ANHYT, KCHOL, SAHOL, EKGYO, ISGYO, BIMAS, TUPRS,
EREGL, FROTO, TCELL, ENKAI, ULKER, SISE. Dönem: son 5 çeyrek (2025Ç2–2026Ç2) ve son 5 yıl (2021–2025).
İstekler arası en az 3 sn bekleme.

### 1.1 Kullanım koşulları

| Kaynak | Koşul | Herkese açık sitede kullanılabilir mi? |
|---|---|---|
| yfinance / Yahoo | Otomatik çekim izinsiz yasak; ticari kullanım ve yeniden dağıtım yasak | **Hayır** |
| isyatirimhisse | "Yalnızca kişisel kullanım"; resmi İş Yatırım kütüphanesi değil | **Hayır** |
| borsapy | "Yalnızca kişisel kullanım ve eğitim; ticari kullanım için BIST'ten lisans" | **Hayır** |
| İş Yatırım sitesi | Kullanım koşulları sayfası bulunamadı (404) | Doğrulanamadı → Hayır varsayılmalı |
| Borsa İstanbul | Site içeriği yazılı izinsiz kopyalanamaz/dağıtılamaz; gecikmeli fiyat dahil web yayını lisanslı | Fiyat: **lisans gerekir** |
| KAP | Bildirimler herkese ücretsiz açık; otomatik çekim/yeniden yayın için yazılı koşul bulunamadı | **Doğrulanamadı** |

Hiçbir kaynak resmi bir istek sınırı yayınlamıyor.

### 1.2 Kaynakların yapısı (kanıtlı)

- **Gerçekte iki bağımsız kaynak var:** borsapy'nin finansal tabloları da İş Yatırım'ın `MaliTablo`
  uç noktasından geliyor. Smoke testte (3 hisse) isyatirimhisse ↔ borsapy farkı varlık, özkaynak,
  net kâr, satış, nakit akışı ve faizde **0**.
- **İş Yatırım `MaliTablo`:** en az 4 dönem istenmezse **boş liste döner, hata vermez**.
  Çeyrekler **kümülatif**. Gruplar: `XI_29` sanayi/holding/GYO, `UFRS` banka-sigorta **solo**,
  `UFRS_K` banka-sigorta **konsolide** (GARAN toplam varlık UFRS 4.412 mlr, UFRS_K 5.216 mlr = yfinance).
- **borsapy `last_n=5` → 4 dönem döner** (4'lü gruplar; tek kalan dönem boş döner, sessizce atılır).
  Bankalar için dokümanında önerilen `UFRS` solo tabloyu verir.
- **isyatirimhisse** zaman aşımını (10 sn sabit) ve "veri yok"u aynı hatayla bildirir;
  `truststore` yoksa SSL doğrulamasını kapatır. İş Yatırım bugün yavaştı (ilk koşuda 17 zaman aşımı).
- **Banka/sigorta tablosunda nakit akışı yok.** Bankada takipteki krediler 0 geliyor, SYR kalemi yok.
- **Para birimi:** yfinance `financialCurrency` THYAO ve ENKAI için **USD** (fiyat TRY). THYAO'da
  İş/yfinance oranı ≈ USD/TRY kuru.
- **En güncel dönem:** Haziran 2026 (2026/6) İş Yatırım, borsapy ve yfinance çeyrekliğinde mevcut
  (Actions koşusunda 20 hissenin 19'unda İş ve borsapy'de, 20'sinde yfinance çeyreklikte; TUPRS zaman aşımı). yfinance yıllıkta
  en güncel 2025/12 (TCELL'de 2024/12). Eylül 2026 henüz hiçbir kaynakta yok (beklenen).

### 1.3 Eksik oran / kaynaklar arası fark tablosu

Kaynak: `docs/faz0/actions/` (`summary.md`, `coverage.csv`, `diffs.csv`, `per_ticker.csv`, `raw_values.csv`).
Actions koşusu, 12 Ekim 14:40–15:22 UTC. İlk yerel koşunun tablosu iki script hatası nedeniyle
geçersiz sayılıp silindi (LEARNING.md adım 0.10).

**Eksik oranı** (hedef hücre = hisse × dönem; 0 = tam, 1 = hiç yok). Sanayi 16 hisse, finansal 4 hisse (2 banka, 2 sigorta).

| Aile | Kalem | isyatirimhisse Ç / Y | borsapy Ç / Y | yfinance Ç / Y |
|---|---|---|---|---|
| sanayi | 7 kalemin hepsi | 0,10 / 0,11 | 0,25 / 0,25 | 0,06 / 0,20 |
| finansal | varlık, özkaynak, net kâr | 0 / 0 | 0,20 / 0,20 | 0,15 / 0,20 |
| finansal | finansal borç, faiz | 0,50 / 0,50 (aileye göre uygulanamaz) | 0,60 / 0,60 | 0,15–0,60 |
| finansal | satış, işletme nakit akışı | 1 / 1 (tabloda yok) | 1 / 1 | 0,15–0,55 |

Eksiklerin nedeni (kanıtlı):
- **isyatirimhisse sanayi %10:** tamamı **TUPRS** (1/16 hisse = %6) + tek tük yıllar. TUPRS'te 9 denemenin
  6'sı İş Yatırım zaman aşımı; koşu boyunca 31 zaman aşımı oldu (yerelde de 17). Kaynak eksik değil, **yavaş/kararsız**.
- **borsapy %25:** `last_n=5` → 4 dönem (5. dönem sessizce düşüyor, yapısal %20) + TUPRS.
- **yfinance yıllık %20:** yalnızca 4 yıl veriyor (2021 yok); TCELL'de yıllık en güncel 2024/12.
- **Finansallarda satış/nakit akışı:** İş tablosunda bu bölümler yok; yfinance bazı bankalarda "Total Revenue" veriyor
  ama tanımı belirsiz.

**Kaynaklar arası fark:**

| Karşılaştırma | Sonuç |
|---|---|
| isyatirimhisse ↔ borsapy | Varlık, özkaynak, net kâr, satış, nakit akışı, faiz: **128/128 birebir** (aynı uç nokta). Borçta 14 fark yalnızca AGESA/ANHYT'de — script'in sigorta eşlemesi (yalnız ilk "Finansal Borçlar" satırı), kaynak farkı değil. |
| İş ↔ yfinance (TRY raporlayanlar) | 2022–2024 yıl sonları ve **tüm çeyreklerde oran tam 1,0000**. **Tek fark 2025/12: ×1,1776** (varlık, özkaynak, net kâr, satış hepsinde) = TMS 29 katsayısı: İş 2025/12'yi Haziran 2026 raporunun yeniden ifade edilmiş rakamıyla güncellemiş, yfinance yıllık raporun rakamında kalmış. 2021/12 ayrıca tutarsız. |
| İş ↔ yfinance (THYAO, ENKAI) | Oran yıl sonu USD/TRY kuru: 18,7 (2022) → 29,5 → 46,2 → 50,5 (2025). yfinance tabloları **USD**. |
| Faiz gideri | Karşılaştırılamaz: İş "Finansman Giderleri" (negatif, kur farkı vb. dahil), yfinance "Interest Expense" (pozitif); %75'inde işaret ters, mutlak oran medyanı ~1,7. |
| Satış (çeyrek) medyan fark %25 | Kümülatiften tekil çeyreğe çevirirken 2025Ç4 = 2025/12 (yeniden ifade edilmiş) − 2025/9 (edilmemiş) çıkıyor → **bazlar karıştığı için Ç4 bozuk**. |

---

## 2. İş Yatırım ↔ KAP (5 hisse)

Ayrıntı: `docs/faz0/kap_vs_isyatirim.md`, ham: `kap_vs_isyatirim.csv`.

- **2026/6:** THYAO, ASELS, GLRMK, TMSN'de toplam varlık, satış, net kâr, özkaynak **birebir aynı**.
- **Eski yıl sonları:** İş = KAP × sabit katsayı, şirketten bağımsız: 2025/12 ×1,1776,
  2024/12 ×1,3089, 2023/12 ×1,4438. Katsayılar **TÜFE ile örtüşüyor** (Oca–Haz 2026 çarpımı 1,1775;
  2025 yıllık %30,89; 2024 yıllık %44,38).
- **Neden:** İş Yatırım her dönemi, onu karşılaştırmalı sütun olarak veren bir sonraki raporun
  **TMS 29 ile yeniden ifade edilmiş** rakamıyla gösteriyor; KAP özet sayfası ilk yayımlanan rakamı.
  → Aynı İş cevabındaki sütunlar farklı TL bazında; kümülatiften tekil çeyrek türetmek ve YoY bozulabilir.
- **Bankalar (GARAN):** 2023–2025 net kâr birebir (bankalar TMS 29 uygulamıyor).
- **Doğrulanamayan:** THYAO 2023/12'nin aynı çıkması; GARAN 2026/6 KAP sayfasının 1000 kat küçük
  okunması (büyük ihtimalle `kap_provider.py` banka formatında çarpanı yanlış okuyor).

---

## 3. GitHub Actions'tan erişim

- Workflow: `.github/workflows/faz0-source-test.yml`, dal `faz0-veri-testi` (commit 8e7ef32),
  run 38264568323. DB secret'ı yok, repoya commit'lemez, sonuç artifact + Summary sayfası.
- **Sonuç: koşu yeşil (pipefail açık → gerçekten hatasız), 42 dk. Bulut IP'sinden (Azure, ubuntu runner)
  beş uç noktanın beşi HTTP 200:**

| Uç nokta | Durum | Süre | Not |
|---|---|---|---|
| Borsa İstanbul CSV | 200 | 1,98 sn | 591 hisse, XYLDZ 149, XUTUM 582 (yerelle aynı) |
| İş Yatırım MaliTablo | 200 | 1,29 sn | 147 kalem; ama koşu boyunca 31 zaman aşımı (10 sn) |
| KAP ana sayfa | 200 | 1,48 sn | |
| KAP şirket listesi (`bist-sirketler`) | 200 | 1,57 sn | Statik HTML. KAP `/tr/api/*` ve JS ile yüklenen finansal tablo sayfası bulutta **test edilmedi** |
| Yahoo chart | 200 | 0,19 sn | |

- 20 hissenin 19'unda İş Yatırım + borsapy verisi geldi (TUPRS hariç, zaman aşımı). Bulutta engelleme belirtisi yok;
  yerelle aynı sonuçlar.
- Artifact ve log indirmek token istiyor (HTTP 403); 13 Ekim'de kullanıcının bu bilgisayardaki git kimlik bilgisiyle
  yalnızca okuma amaçlı indirildi.

---

## 4. Evren sorunu (290 vs 149)

| Soru | Cevap | Kanıt |
|---|---|---|
| Evren nereden geliyor? | `sector_peers.load_universe()` → `bist_universe_provider` → BIST `hisse_endeks_ds.csv`, endeks kodu **XYLDZ**; hata olursa bayat cache → statik `data/bist_universe.txt` (270) | kod |
| 149 nereden? | Resmi CSV'de XYLDZ **bugün gerçekten 149 hisse** (CSV tarihi 12/10/2026; XUTUM 582, toplam 591) | CSV |
| ~290 nereden? | Büyük ihtimalle DB'deki tüm zamanların farklı hisse sayısı (**291**); Ağustos'ta cache 271, statik liste 270 | DB (salt-okuma) |
| Actions CSV'de başarısız oluyor mu? | **Hayır.** 11 ve 12 Ekim koşuları 149'luk listeyle taradı, DB'ye 148 yazdı (eksik: MASFN) | DB + Actions API |
| Eski listeye sessizce düşüyor mu? | Bu koşularda düşmüyor. Ama düşme zinciri sessiz (yalnızca `print("UYARI")`) | kod |
| **XYLDZ = Yıldız Pazar mı?** | **Hayır.** Temmuz 2026'da Yıldız Pazar'a geçen CGCAM, MERIT, NETCD, YATAS, ENDAE XYLDZ'de yok (XU500/XUTUM'da var) | CSV + haber |
| 271 → 149 neden? | **Doğrulanamadı** | — |

**Ek bulgu — sessiz yeşil taramalar:** 14 Ağustos–10 Ekim arası ~24 zamanlanmış `scan.yml` koşusu
"success", ama tarama adımı **4 sn** sürmüş ve DB'ye **hiç kayıt yazılmamış**. Neden: `python … | tee`
ve varsayılan `bash -e` kabuğunda `pipefail` yok. Python'un neden çöktüğü doğrulanamadı (log 403).
Ayrıca `fetch_universe_market_data` yfinance hatasında `except: continue` ile hisseyi sessizce atıyor.

---

## 5. Bölüm 12 açık soruları

| Soru | Cevap |
|---|---|
| İş Yatırım'dan çeyreklik tablolar, nakit akışı, faiz gideri, banka metrikleri geliyor mu? | **Çeyreklik: evet** (kümülatif). **Nakit akışı: sanayide evet** (`4C`), banka/sigortada **yok**. **Faiz gideri:** sanayide yalnızca "Finansman Giderleri" (`4BB`/`3HC`, saf faizden geniş), bankada "Faiz Giderleri" (`3B`). **Banka metrikleri:** NFM hesaplanabilir (faiz gelir/gider var), maliyet/gelir kısmen; **SYR yok, takipteki kredi 0**, kredi/mevduat ve özkaynak/aktif hesaplanabilir. Ancak karar gereği İş Yatırım canlıda kullanılmayacak. |
| Pay sayısı hangi kaynaktan? | Adaylar: İş "Ödenmiş Sermaye" (1 TL nominal → adet; THYAO 1,380 mlr, GARAN 4,2 mlr), yfinance `sharesOutstanding` (THYAO 1,372 mlr — geri alınan paylar düşülmüş olabilir), borsapy (piyasa değeri / fiyat, türetilmiş). **Yasal kaynak kararıyla:** KAP'taki sermaye bilgisi aday; KAP'tan çekilebildiği **doğrulanmadı**. |
| Karşılaştırma dönemleri TMS 29 bazında aynı bazda mı? | **Hayır.** İş Yatırım her yıl sonunu farklı tarihin TL'si ile veriyor (TÜFE katsayılarıyla kanıtlı); KAP özet sayfası ilk yayımlanan rakamı veriyor. Aynı bazda YoY için cari raporun karşılaştırmalı sütunu kullanılmalı. 2025/6'nın 2026/6 ile aynı bazda olduğu **doğrulanmadı**. |
| Actions IP'lerinden İş Yatırım, KAP, BIST CSV erişimi? | **Evet, üçü de (HTTP 200)**, run 38264568323. İş Yatırım bulutta da yavaş (31 zaman aşımı). KAP'ın JS ile yüklenen finansal tablo sayfası ve `/tr/api/*` uç noktaları bulutta **test edilmedi**. |
| KAP sektör sınıflandırması: pykap mı kap-mcp mi? | **pykap:** sektör alanı yok. **kap-mcp 0.1.0:** KAP taksonomisini (16 ana → 48 alt sektör) ve 605 şirketlik eşlemeyi statik JSON olarak taşıyor (2026-04-22, tek sürüm, PyPI'da lisans alanı boş). İkisi de çalıştırılarak test edilmedi. **KAP ana sektörü ailelerle uyuşmuyor:** holding, GYO, sigorta, banka hepsi "MALİ KURULUŞLAR"; **SISE "Holdingler"** altında. |
| Evren: ~290 vs 149 farkı? | Bölüm 4. |
| Kaynakların kullanım koşulları ve istek sınırları? | Bölüm 1.1. Hiçbiri resmi istek sınırı yayınlamıyor. |

---

## 6. Belgede değişmesi önerilen yerler (belge değiştirilmedi)

1. **§2.5 ve §9 "Veri: yfinance + İş Yatırım hibrit"** → herkese açık site + yasal kaynak kararıyla
   çelişiyor. Önerilen: "Finansal tablolar: KAP (yasal durumu yazılı olarak teyit edilecek).
   yfinance, İş Yatırım, borsapy yalnızca geliştirme/doğrulama için, canlıda kullanılmaz."
2. **§2.1 ve §4 Değerleme (%25) + Momentum (%15)** → fiyat verisi lisanslı; "ücretsiz" kararıyla
   ücretsiz yasal fiyat kaynağı bulunana kadar bu iki pillar "veri lisansı yok" olarak gösterilmeli,
   ağırlıklar Kalite/Güvenlik'e yeniden dağıtılmalı ya da toplam skor yalnızca iki pillar ile tanımlanmalı.
   §7 piyasa değeri, likidite, beta ve §10.4 (F/K, F/DD elle kontrol) de aynı nedenle etkilenir.
3. **§3 Aileler/karşılaştırma grupları "KAP ana sektöründen türetilir"** → ana sektör yetmez
   (holding/GYO/sigorta/banka aynı ana sektörde, SISE holding sayılıyor). Aile ataması: KAP alt
   sektör + tablo formatı (sanayi / BDDK / sigorta). SISE gibi istisnalar için elle düzeltme listesi.
4. **§9 Evren "resmi Borsa İstanbul CSV'si"** → XYLDZ endeks kodu Yıldız Pazar'ın tamamı değil.
   Evren tanımı netleşmeli (XYLDZ endeksi mi, Yıldız Pazar segmenti mi, XUTUM mu); CSV'yi sitede
   yeniden yayınlamanın izne tabi olup olmadığı sorulmalı.
5. **§9 Tarama kuralı** → mevcut `scan.yml` bu kuralı ihlal ediyor (pipefail yok, log repoya
   commit'leniyor). Belgeye "her koşu sonunda DB'ye yazılan kayıt sayısı kontrol edilir; 0 ise kırmızı" eklenmeli.
6. **§4 Reel gelir büyümesi, marj istikrarı, YoY marj** → TMS 29 bazı sorunu (bölüm 2) nedeniyle
   "hangi dönemin hangi rapordan alındığı" kuralı eklenmeli: YoY için cari raporun karşılaştırmalı sütunu.
7. **§5 Bankalar** → SYR ve takipteki kredi KAP finansal tablosunda yok (kap-mcp README'si de
   "SYR BDDK raporlarında" diyor). Bu iki metrik "uygulanamaz" ya da ayrı kaynak (BDDK) olarak işaretlenmeli.
8. **§9 Para birimi** → kural doğru ve gerçek vakası var (THYAO, ENKAI); yfinance canlıdan çıkınca
   kural "KAP sunum para birimi ve birim çarpanı (bin/milyon TL) okunur" şekline dönmeli.
9. **§11 Takvim** → Faz 1 "yeni veri katmanı" KAP'a geçişle birlikte 14-18 Ekim'e sığmayabilir;
   yasal teyit (KAP/BIST'e yazılı soru) Faz 1'in önüne konmalı.
10. **§13 Dürüst sınırlar** → "Veri kaynakları ve lisans durumu" maddesi eklenmeli.

---

## 7. Ek inceleme (13 Ekim 2026)

Kullanıcı kararları: Değerleme ve Momentum yerinde kalır; fiyat yfinance'ten (araştırma/eğitim amaçlı),
ham veri repoya girmez, sitede yalnızca türetilmiş skor. Evren `XYLDZ`. "Son 5 dönem" yorumu doğru.
Ham veriler yalnızca yerel `.faz0/` altında (git dışı).

### 7.1 Kaynak koşulları — metin + robots.txt

| Kaynak | Metin (aktarım) | robots.txt |
|---|---|---|
| Yahoo / yfinance | yfinance README: *"intended for research and educational purposes"*, *"the Yahoo! finance API is intended for personal use only"*. Yahoo ToS: otomatik erişim *"without our express, prior permission"* yasak; ticari amaçla erişim/yeniden kullanım ve dağıtım yasak. | `query1.finance.yahoo.com`: `Disallow: /` (tüm botlar) |
| İş Yatırım | *"Bu içeriğe ilişkin tüm telif hakları İş Yatırım Menkul Değerler A.Ş.'ye aittir."*; *"BIST piyasalarında oluşan tüm verilere ait telif hakları tamamen BIST'e ait olup, bu veriler tekrar yayınlanamaz."* Kullanım koşulları sayfası 404. | `Disallow: /_layouts/` — `MaliTablo` bu yolun altında |
| KAP | Kullanım koşulları metni bulunamadı. | Hata sayfası (666/500) — doğrulanamadı |
| Borsa İstanbul | Yazılı izinsiz *"kısmen veya tamamen kopya edilemez, uygulamaya konulamaz, dağıtılamaz"*; gecikmeli veri dağıtımı için alt dağıtıcı yetkisi. | `Allow: /` |

Üç soru (kişisel kullanım / türetilmiş sonucu yayınlama / otomatik istek) için metinlerde açık cevap
bulunmayan her hücre "doğrulanamadı". Hukuki yorum yapılmadı.

### 7.2 Eksiklik matrisi (20 hisse; sanayi 16 · finansal 4)

| Kalem | yfinance | İş Yatırım | KAP özet sayfa |
|---|---|---|---|
| geçmiş yıllar kârı | 15 · 4 | 16 · 4 | 0 · 0 |
| dönen varlıklar | 14 · 0 | 16 · 2 | 16 · 0 |
| EBIT | 14 · 0 | 16 · 0 | 16 · 0 |
| işletme nakit akışı | 15 · 2 | 16 · 0 | 0 · 0 |
| faiz gideri | 15 · 2 | 16 · 2 | 0 · 0 |
| finansal borç | 15 · 4 | 16 · 2 | 0 · 0 |
| çeyreklik net kâr | 11 · 1 | 16 · 4 | 16 · 2 (yalnız son ara dönem) |
| çeyreklik satış | 11 · 1 | 16 · 0 | 16 · 0 |
| özkaynak | 15 · 4 | 16 · 4 | 16 · 0 |

### 7.3 TTM "veri yok" (AEFES, ARCLK, FROTO, EREGL, ASELS, GARAN)

yfinance'te altısında da 2025-09-30 çeyreğinin gelir tablosu boş (yalnızca nakit akışı dolu); 20 hissede
bu çeyrek 13'ünde var. `normalizer.get_ttm_financials` bu çeyreği "dolu" sayıyor (herhangi bir akış kalemi
yeterli), sonra net kâr/satış/EBIT için 4 çeyreğin hepsini arayıp `None` dönüyor. Neden kaynak boşluğu; kod
yanlış sayı üretmiyor ama "dolu çeyrek" kontrolü yanıltıcı ve telafi yolu yok. GARAN'da ayrıca bankada
brüt kâr/EBIT hiç yok. KAP köprülemesi devreye girmedi (KAP ile yfinance'in son dönemi aynı); formülü doğru
ama TMS 29 birimlerini karıştırıyor.

### 7.4 Z-Score / Piotroski girdileri İş Yatırım'dan

Sanayi için türetilebilir. 2024/12'de yfinance ile birebir: Dönen Varlıklar, Kısa Vadeli Yükümlülükler,
Toplam Yükümlülükler (KV + UV), Brüt Kar, UV Finansal Borçlar (ASELS). Eşleşmeyen: geçmiş yıllar kârı ve
EBIT (tanım farkı); pay sayısı BIMAS'ta (sonradan bedelsiz). Seçilen tanımlar `docs/scoring-v3.md` §4'te.
EBIT için `3DF` "FAALİYET KARI (ZARARI)" = KAP "ESAS FAALİYET KARI (ZARARI)" (ASELS 2026/6 birebir);
TMS 29 net parasal pozisyon bu satırın dışında (KAP raporunda finansman giderlerinden sonra).

### 7.5 TMS 29 birimleri

×1,1776 = TÜFE(Haziran 2026) / TÜFE(Aralık 2025) (Oca–Haz 2026 aylık TÜFE çarpımı 1,1775).
İş Yatırım 2025/12, 2025/6 ve 2026/6 → Haziran 2026 TL'si (2025/6 KAP karşılaştırmalı sütunuyla birebir: ASELS
satış 70.956.004 bin TL); 2026/3 → Mart 2026 TL'si (ASELS'te 2026Ç2 = 2026/6 − 2026/3 × 1,0702 = KAP 3 aylık sütunu).
yfinance 2025/12 yıllık → Aralık 2025 TL'si; 2026Ç2 çeyrekleri çoğu TMS 29 şirketinde KAP 3 aylık sütunu.
**yfinance ASELS 2026Ç2 hatalı:** satış ve net kâr önceki yılın 6 aylık rakamı. EREGL 2024/12'de iki kaynak ×1,31 farklı.
Etki: YoY ve büyüme farklı birimdeki sütunlarla bozulur; F/DD ve F/K'da defter değeri/kâr birimi fiyatla
uyuşmazsa ×1,18'e varan kayma; ROE aynı sütundan hesaplanırsa etkilenmez, kaynak/sütun karışırsa ~%18 kayar.

### 7.6 yfinance "tam" şartı sayımı

Şart: son 5 çeyrek + son 2 yıllık, TRY, gerekli kalemler dolu, en güncel dönem 2026/6 ve 2025/12,
bilanço özdeşliği %1, makul aralık. **Sanayi: 6/16 geçti** (EKGYO, KCHOL, SISE, TMSN, TUPRS, ULKER).
Kalanlar: 2025Ç3 boş (ASELS, EREGL, FROTO, ISGYO), para birimi (THYAO USD, ENKAI USD, GLRMK boş),
UV borç satırı yok (BIMAS, ENKAI), dönen varlık/EBIT yok (SAHOL), 2025 yıllığı yok (TCELL).
Finansalların hiçbiri geçmiyor (format farkı). **Öneri: finansal tablolar için İş Yatırım tek ana kaynak.**

### 7.7 Sitedeki ~290 hisse

v2 sitesi (`app.py` `load_latest_pillar_scores`) her hissenin en son koşusunu yaş filtresi olmadan gösteriyor;
Ağustos'taki 270–288 hisselik taramalardan kalan hisseler de listede. 12 Ekim'de DB'de 291 farklı hisse vardı.
