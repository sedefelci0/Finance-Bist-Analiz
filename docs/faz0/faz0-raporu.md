# Faz 0 Raporu — Veri kaynakları ve evren

Tarih: 12 Ekim 2026. Karar belgesi: `docs/scoring-v3.md`. Adım adım gerekçeler: `LEARNING.md`.

> **Durum:** 2, 4, 5 ve 6. adımlar tamamlandı. 1. adımın 20 hisselik düzeltilmiş koşusu ve
> 3. adımın Actions koşusu rapor yazılırken sürüyordu; sonuçları bu rapora **henüz girmedi**
> (bkz. `docs/faz0-devir-notu.md`, "Yarım kalanlar").

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
  (ilk koşuda 20 hissenin 18'inde İş'te görüldü; eksikler zaman aşımı kaynaklıydı). yfinance yıllıkta
  en güncel 2025/12 (TCELL'de 2024/12). Eylül 2026 henüz hiçbir kaynakta yok (beklenen).

### 1.3 Eksik oran / kaynaklar arası fark tablosu

**Sonuç bekleniyor.** Düzeltilmiş 20 hisselik koşu `docs/faz0/local/` altına
`summary.md`, `coverage.csv`, `diffs.csv`, `per_ticker.csv`, `raw_values.csv` yazacak.
İlk koşunun tablosu iki script hatası nedeniyle geçersiz sayılıp silindi (LEARNING.md adım 0.10).

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
- **Sonuç bekleniyor.**
- **Dolaylı kanıt (mevcut):** canlı `scan.yml` 11 ve 12 Ekim'de Actions'tan Borsa İstanbul CSV'sine
  erişti (149 hisse) ve DB'ye 148 hisse yazdı. KAP ve İş Yatırım için bulut erişimi henüz ölçülmedi.
- Not: Actions log'ları ve artifact'ları token olmadan indirilemiyor (HTTP 403).

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
| Actions IP'lerinden İş Yatırım, KAP, BIST CSV erişimi? | **BIST CSV: evet** (canlı tarama kanıtı). İş Yatırım ve KAP: **sonuç bekleniyor** (run 38264568323). |
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
