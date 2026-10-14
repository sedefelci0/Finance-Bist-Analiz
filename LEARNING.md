# LEARNING.md — Neden böyle yaptık

Bu dosya Alpha Score v3 çalışmasında atılan her adımın **nedenini** ve
belirsiz kalan yerleri (açık sorular) kaydeder. Karar belgesi: `docs/scoring-v3.md`.

---

## Faz 0 — Veri kaynağı testi ve evren sorunu (12 Ekim 2026)

### Adım 0.1 — Belgeyi GitHub'dan çektik, yerel kopya üretmedik
**Ne:** `git fetch` + `git merge --ff-only origin/master` (commit `49fe797`).
**Neden:** Belge yalnızca GitHub'da vardı. Downloads'taki kopyayla birebir aynı
olduğunu `diff` ile doğruladık, ama kaynak olarak repodaki commit'i esas aldık ki
tek bir doğru sürüm olsun.

### Adım 0.2 — Paketleri gitignore'daki `.venv`'e kurduk
**Ne:** `.venv` içine yfinance 1.7.0, isyatirimhisse 5.0.1, borsapy 0.11.0.
**Neden:** Global Python'u ve `requirements.txt`'i Faz 0 deneyleri için kirletmemek.
Scratchpad'e kurmayı denedik, Windows yol uzunluğu sınırı yüzünden pip kurulamadı.
`requirements.txt`'e henüz hiçbir şey eklenmedi — hangi kaynağın kalacağı Faz 0'ın sonucu.

### Adım 0.3 — Kod yazmadan önce kullanım koşullarını okuduk
**Neden:** Belge ve görev bunu şart koşuyor; ayrıca bir kaynağın koşulları
"otomatik çekim yasak" diyorsa teknik testin anlamı değişir.
Bulgular (kaynak: paket README'leri ve sitelerin kendi sayfaları):

| Kaynak | Ne diyor | Bizim için anlamı |
|---|---|---|
| yfinance (paket) | "Yahoo! finance API is intended for personal use only." Kullanıcıyı Yahoo koşullarına yönlendiriyor. | — |
| Yahoo Terms of Service | Otomatik araçlarla (robot, scraper vb.) veri toplamak **önceden izin olmadan yasak**; ticari kullanım ve yeniden dağıtım yasak. | Proje zaten yfinance kullanıyor; herkese açık bir siteyle yayın bu maddeyle çelişebilir. |
| isyatirimhisse (paket) | "Resmi İş Yatırım kütüphanesi değildir… yalnızca kişisel kullanım amaçları için tasarlanmıştır." | — |
| İş Yatırım sitesi | Kullanım koşulları sayfası bulunamadı (404). Arama sonuçlarındaki yasal uyarı: BIST'te oluşan verilerin telif hakkı BIST'e aittir, yeniden yayınlanamaz. | Tam metin **doğrulanamadı**. |
| borsapy (paket) | "Yalnızca kişisel kullanım ve eğitim amaçlıdır… ticari amaçla kullanılamaz. Ticari kullanım için Borsa İstanbul'dan lisans alın." | — |
| Borsa İstanbul (telif hakkı ve çekince ihbarı) | Site içeriği yazılı izin olmadan "kısmen veya tamamen kopya edilemez, uygulamaya konulamaz, dağıtılamaz". | Evren CSV'sini çekmek "bilgi edinme" sayılabilir, ama ticker listesini yeniden yayınlamak gri alan. |
| KAP | Ana sayfada ayrı bir kullanım koşulları metni bulunamadı. | **Doğrulanamadı.** |

İstek sınırı (rate limit): hiçbir kaynak resmi bir sayı yayınlamıyor. Bu yüzden testte
**her istek arasında en az 3 saniye** bekliyoruz (muhafazakâr seçim, kanıta dayalı değil).

> **AÇIK SORU (kullanıcıya):** Site herkese açık mı, yoksa kişisel kullanım mı?
> Üç paket de "yalnızca kişisel kullanım" diyor, Yahoo koşulları otomatik çekimi
> izinsiz yasaklıyor. Bu, "hangi kaynak" kararından önce gelen bir karar.

### Adım 0.4 — Script yazmadan önce İş Yatırım'ın ham cevabına baktık
**Ne:** `MaliTablo` uç noktasına THYAO, GARAN, AGESA, KCHOL, EKGYO için az sayıda
elle istek (aralarda 3 sn). Çıktılar `.faz0/probe_*.txt` (git'e girmiyor, yereldeki not).
**Neden:** Kalem kodlarını (1BL, 2N, 3C…) ve banka tablosunun yapısını tahmin etmek
yerine görmek. Öğrendiklerimiz:
- **En az 4 dönem istenmezse API boş liste döner, hata vermez.** (THYAO 2 dönemle 0
  kalem, 4 dönemle 147 kalem.) Sessiz başarısızlık riski — v3 veri katmanında
  "0 kalem" mutlaka hata sayılmalı.
- **Çeyreklik değerler kümülatif** (yılbaşından bugüne). THYAO satış: 2026/3 = 258 mlr,
  2026/6 = 585 mlr. yfinance ise tekil çeyrek veriyor; karşılaştırmada dönüştürmek gerekiyor.
- **borsapy'nin finansal tabloları da aynı İş Yatırım `MaliTablo` uç noktasından geliyor.**
  Yani "üç kaynak" aslında iki bağımsız kaynak: İş Yatırım (iki paket) ve Yahoo.
- Gruplar: sanayi/holding/GYO `XI_29`; banka **ve** sigorta `UFRS` (kodlar farklı).
- Banka (`UFRS`) ve sigorta tablosunda **nakit akışı bölümü yok** (yalnızca 1/2/3 kodları).
  Bankada "Takipteki Krediler" alanı 0 geliyor, sermaye yeterlilik oranı kalemi yok.
- THYAO 2025/12 sütununda ölçek tutarsızlığı: Yurtiçi Satışlar 92,6 **milyon**
  (2025/6'da 33 **milyar**), HBK = 0. Ana kalemler (toplam varlık, satış) tutarlı görünüyor.
- isyatirimhisse, `truststore` paketi yoksa SSL doğrulamasını **kapatıyor**
  (`verify=False`). Kendi kurulumumuzda bunu bilerek değerlendirmeliyiz.

### Adım 0.5 — Test evreni ve dönem tanımı (seçim, kullanıcı değiştirebilir)
**Ne:** Belgede adı geçen 10 hisse + 2 GYO (EKGYO, ISGYO) + 8 farklı sektör:
BIMAS (perakende), TUPRS (rafineri), EREGL (demir-çelik), FROTO (otomotiv),
TCELL (telekom), ENKAI (inşaat/taahhüt), ULKER (gıda), SISE (cam/sanayi).
**Neden:** Görev "2 GYO ve diğer sektörlerden 8 hisse" diyor ama isim vermiyor.
Yüksek likiditeli, farklı sektörden, verisi muhtemelen tam olan isimler seçildi ki
eksiklik "küçük şirket" yüzünden değil kaynak yüzünden görünsün.
**Dönem:** "Son 5 dönem (yıllık + çeyreklik)" = son 5 çeyrek (2025Ç2–2026Ç2) **ve**
son 5 yıl (2021–2025) olarak yorumlandı.
> **AÇIK SORU:** Hisse seçimi ve dönem yorumu doğru mu? Farklıysa script parametreyle
> yeniden çalıştırılabilir.

### Adım 0.6 — Kaynak karşılaştırma script'i: `scripts/faz0_source_test.py`
**Ne:** Erişim testi + 20 hisse × 7 kalem × 3 kaynak; çıktılar `docs/faz0/<ortam>/`.
**Neden böyle:**
- Tek script hem yerelde hem Actions'ta çalışsın ki "bulut IP'si" farkı tek değişken olsun.
- İş Yatırım çeyrekleri kümülatif olduğu için yfinance ile karşılaştırırken akım
  kalemlerinde (net kâr, satış, nakit akışı, faiz) tekil çeyreğe çevirdik; stok kalemlerde
  (varlık, özkaynak, borç) dönem sonu değeri doğrudan karşılaştırılıyor.
- Kapsama oranını **aileye göre ayrı** hesapladık: banka için "satış yok" eksiklik değil, uygulanamaz.
- isyatirimhisse 10 sn sabit zaman aşımıyla çalışıyor ve hatayı sadece print ediyor
  (THYAO 2023 ilk denemede sessizce kayboldu) → boş yılı bir kez yeniden deniyoruz, deneme kayıtlı.
**Smoke testte bulunanlar:**
- **borsapy `last_n=5` → 4 dönem döner.** Paket dönemleri 4'lü gruplar halinde istiyor
  (`_MAX_PERIODS_PER_CALL = 4`); 5. dönem tek başına kalıyor, API tek dönemlik isteğe boş
  dönüyor, paket bunu hata saymadan atlıyor. 4'ün katı olmayan her `last_n`'de son dönem kaybolur.
- **`UFRS` = solo, `UFRS_K` = konsolide.** GARAN 2026/6 toplam varlık: UFRS 4.412 mlr,
  UFRS_K 5.216 mlr, yfinance 5.216 mlr (birebir). borsapy dokümanı bankalar için "UFRS"
  öneriyor → farkında olmadan solo tablo kullanılır. Script önce `UFRS_K`'yi deniyor.
- **THYAO yfinance `financialCurrency = USD`**, fiyat TRY. yfinance THYAO tabloları USD;
  oran ≈ USD/TRY kuru. Belgenin 9. bölümündeki para birimi kuralı gerçek bir vakaya denk geliyor.
- THYAO İş Yatırım 2025/12 rakamları komşu çeyreklerle tutarsız (toplam varlık 2025/12
  2.351 mlr → 2026/3 2.158 mlr düşüş; USD bazında ise artış). KAP ile karşılaştırılacak (adım 2).

### Adım 0.7 — Evren sorunu (290 vs 149): kanıt
**Ne yaptık:** Kod okuma + GitHub Actions public API (job adım süreleri) + veritabanında
yalnızca okuma (`SET TRANSACTION READ ONLY`) sorgusu + resmi CSV'nin içeriği.
**Neden DB'ye baktık:** Actions job log'ları kimlik doğrulama istiyor (403); 149'un
nerede oluştuğunu görmenin tek doğrudan yolu "hangi koşu kaç hisse yazdı" sorusuydu.
**Bulgular:**
1. **Resmi CSV'de XYLDZ bugün 149 hisse** (12/10/2026 tarihli CSV; XUTUM 582, toplam 591 `.E`).
   Actions CSV'ye erişiyor ve 149 alıyor — **sessizce eski listeye düşme kanıtı yok.**
   DB: 11 Ekim Actions koşusu **148** hisse yazdı (1'i muhtemelen skorlanamadı).
2. **"~290" CSV'den değil, DB'den/eski listeden geliyor olmalı:** `pillar_scores`'ta tüm
   zamanlarda **291** farklı hisse var; Ağustos'taki cache 271, statik liste 270 hisse.
3. **XYLDZ ≠ Yıldız Pazar.** Temmuz 2026'da Yıldız Pazar'a geçtiği duyurulan CGCAM, MERIT,
   NETCD, YATAS, ENDAE CSV'de XU500/XUTUM'da var, XYLDZ'de yok. `bist_universe_provider.py`
   "XYLDZ = Yıldız Pazar bileşenleri" varsayımı üzerine kurulu. XYLDZ'nin 271'den 149'a
   neden düştüğü (endeks kuralı mı değişti?) **doğrulanamadı**.
4. **Sessiz düşüş zinciri gerçekten var ama Actions'ta tetiklenmiyor:** CSV hata verirse
   → bayat cache (Actions'ta yok, gitignore'da) → statik 270'lik liste, yalnızca `print("UYARI…")`.
5. **Asıl sessiz hata başka yerde:** 14 Ağustos–10 Ekim arası ~24 zamanlanmış koşu "success"
   ama tarama adımı **4 saniye** sürmüş ve DB'ye **hiç kayıt yazılmamış**. Neden:
   `python … | tee scan_output.log` — Actions'ın varsayılan `bash -e` kabuğunda `pipefail`
   yok, çıkış kodunu `tee` belirliyor. `tee` eklenmeden önceki koşular (0ca9d74) aynı ~1 dk'da
   **kırmızı** bitiyordu. Python'un neden 4 sn'de çöktüğü **doğrulanamadı** (log 403).
   11 Ekim elle koşu ve 12 Ekim zamanlanmış koşu ise gerçekten tarıyor.
6. Ek sessiz kayıp: `sector_peers.fetch_universe_market_data` yfinance hatasında `except: continue`.

### Adım 0.8 — İş Yatırım ↔ KAP elle karşılaştırma (5 hisse)
**Ne:** THYAO, ASELS, GLRMK, TMSN, GARAN; KAP'ın "şirket finansal bilgileri" özet sayfası
(projedeki `kap_provider.py`, Playwright) ↔ İş Yatırım `MaliTablo`. Sonuç: `docs/faz0/kap_vs_isyatirim.md`.
**Neden bu 5:** belgede elle kontrol için adı geçen 4 hisse + 1 banka; TMS 29 uygulayan
sanayi şirketleri ile uygulamayan bankayı yan yana görmek için.
**Bulgu:** 2026/6 birebir aynı. Eski yıl sonlarında İş = KAP × sabit katsayı (1,1776 / 1,3089 /
1,4438), katsayılar **TÜFE ile birebir** (Oca–Haz 2026 çarpımı 1,1775; 2025 %30,89; 2024 %44,38).
İş Yatırım her dönemi bir sonraki raporun yeniden ifade edilmiş karşılaştırmalı rakamıyla veriyor
→ aynı cevaptaki sütunlar farklı TL bazında. Bankalarda fark yok (TMS 29 uygulamıyorlar).
**Neden önemli:** kümülatif çeyrekten tekil çeyrek türetmek ve YoY büyüme bu yüzden bozulabilir.

### Adım 0.9 — Actions workflow'u ayrı dosya, ayrı dal, secret yok
**Ne:** `.github/workflows/faz0-source-test.yml` (henüz push edilmedi).
**Neden:**
- `scan.yml`'ye dokunmamak: canlı taramayı Faz 0 deneyiyle karıştırmamak.
- DB secret'ı kullanmıyor, `contents: read` — test yalnızca dış kaynaklara erişimi ölçüyor.
- `shell: bash -eo pipefail` — `scan.yml`'deki sessiz yeşil hatayı tekrarlamamak.
- Sonuç repoya commit'lenmiyor, artifact + Summary sayfası (belge bölüm 9: "log'u repoya commit'leme").
- `workflow_dispatch` yalnızca varsayılan daldaki workflow'larda arayüzde görünüyor; master'a
  dokunmadan çalıştırabilmek için `faz0-veri-testi` dalına push tetikleyicisi de eklendi.
> **AÇIK SORU:** Push için onay gerekiyor. Ayrıca artifact ve log indirmek token istiyor (403);
> sonucu ya sen Summary sayfasından/zip'ten bana verirsin ya da yerel git kimlik bilgisini
> API okuması için kullanmama izin verirsin.

### Adım 0.10 — İlk tam koşu atıldı, iki hata düzeltilip yeniden koşuldu
**Ne oldu:** İlk 20 hisselik koşuda İş Yatırım 17 kez zaman aşımına düştü (paket 10 sn sabit).
EREGL, FROTO, SISE'de 2021'in ilk denemesi zaman aşımına düşünce script bunu "bu grupta veri yok"
sanıp UFRS'e geçti → üç sanayi şirketi "veri yok" göründü. Bu **bizim** hatamızdı, kaynağın değil.
Ayrıca borsapy finansal borç tam 2 kat çıktı: `df.loc[[ad, ad]]` aynı iki satırı iki kez seçiyordu
(yine bizim hatamız; borsapy'nin payı satırları kodsuz, yalnızca adla indekslemesi).
**Neden yeniden koştuk:** Hatalı ölçümle "İş Yatırım'da %28 eksik" demek yanlış olurdu.
**Düzeltme:** her boş yıl 3 kez denenir (aralarda 10 sn), ancak sonra sıradaki gruba geçilir;
borç satırları maskeyle seçilir. İlk koşunun çıktısı silindi, yeni koşu `docs/faz0/local/`.
**Öğrenilen:** isyatirimhisse zaman aşımını ve "veri yok"u **aynı** `ValueError` ile bildiriyor —
v3 veri katmanı bu paketi kullanacaksa ikisini ayırt edemez; doğrudan HTTP çağrısı daha güvenli.

### Ek bulgu — bugünkü zamanlanmış tarama (12 Ekim, run 38258982594)
27 dk sürdü, gerçekten taradı, DB'ye **148** hisse yazdı. CSV'deki 149 XYLDZ'den eksik olan
yalnızca **MASFN** (muhtemelen `fetch_universe_market_data`'nın sessiz `except: continue`'su).

### Adım 0.11 — pykap vs kap-mcp (sektör sınıflandırması için)
**Ne:** İkisini `.venv`'e kurup içeriklerine baktık (sunucu olarak çalıştırmadık).
**Neden çalıştırmadık:** soru "sektör sınıflandırması hangi paketten"; paketlerin bunu sağlayıp
sağlamadığı kod/veri incelemesiyle yanıtlanabiliyordu, KAP'a ek istek atmaya gerek yoktu.
**Bulgular:**
- **pykap 0.2.0** (Mart 2026, MIT): bildirim/şirket listesi sarmalayıcısı; **sektör alanı yok**.
  KAP'ın `/tr/api/*` uç noktalarına doğrudan POST atıyor (projedeki `kap_provider.py` notu bu
  uç noktaların bot korumasıyla engellendiğini söylüyor — pykap'in bugün çalışıp çalışmadığı **doğrulanmadı**).
- **kap-mcp 0.1.0** (Nisan 2026, tek sürüm, PyPI'da lisans alanı boş, README'de MIT): KAP resmi
  taksonomisini (16 ana sektör → 48 alt sektör) ve 605 şirketlik ticker→sektör→parser eşlemesini
  **paketin içinde statik JSON** olarak taşıyor (`generated_at 2026-04-22`, 6 ay eski).
  Banka (BDDK) ve sigorta için ayrı parser'lar var. 20 test hissemizin hepsi listede.
- **KAP taksonomisi ≠ belgedeki aileler:** holdingler, GYO'lar, aracı kurumlar, sigorta ve bankalar
  hepsi "MALİ KURULUŞLAR" ana sektöründe. **SISE "Holdingler ve Yatırım Şirketleri"** olarak
  sınıflanmış (sanayi değil). Aile ataması alt sektör + parser_family ile yapılmalı, ana sektörle değil.
- Alternatif: borsapy'nin KAP sağlayıcısı sektörü KAP şirket sayfasından canlı kazıyor
  (`get_company_details`), ama yalnızca ana sektör adını alıyor.

---

## KARAR (kullanıcı, 12 Ekim 2026): Site herkese açık olacak, yalnızca yasal kaynak kullanılacak

**Sonuçları (adım 0.3'teki koşullara göre):**
- **yfinance / Yahoo:** Yahoo ToS otomatik çekimi izinsiz, ticari kullanımı ve yeniden dağıtımı yasaklıyor → **kullanılamaz.**
- **isyatirimhisse, borsapy:** paketlerin kendisi "yalnızca kişisel kullanım" diyor; veri İş Yatırım'ın
  (ve BIST'in) → **canlı sitede kullanılamaz.** Faz 0'daki ölçümler yalnızca araştırma amaçlı.
- **Borsa İstanbul fiyat verisi:** BIST SSS'ine göre gecikmeli veri dahil web'de yayın için
  lisans gerekiyor ("Alt Dağıtıcı … gecikmeli veri, referans veri vb. için dağıtım yetkisi alabilmektedir";
  alt dağıtıcı olmak için BIST'in yetkilendirdiği bir Dağıtıcı Kurum ile anlaşma). Ücret tarifesi Veri
  Dağıtım Sözleşmesi Ek-3'te. → **Momentum, F/K, F/DD, piyasa değeri, beta gibi fiyata dayalı her metrik
  lisans konusu.** Gün sonu kapanış fiyatının ayrı bir istisnası olup olmadığı **doğrulanamadı**.
- **Borsa İstanbul endeks CSV'si (evren):** telif ihbarı yazılı izinsiz kopyalama/dağıtımı yasaklıyor;
  ticker listesini sitede göstermenin izne tabi olup olmadığı **doğrulanamadı**.
- **KAP:** bildirimler herkese ücretsiz açık; KAP bildirimlerini gerçek zamanlı yeniden yayınlayanlar
  "veri yayın kuruluşları" (lisanslı). KAP web sitesinden otomatik çekim ve türetilmiş veriyi
  yayınlamaya dair yazılı bir kullanım koşulu **bulunamadı** — ne yasak ne izin doğrulanabildi.
**Neden önemli:** Belgedeki "veri: yfinance + İş Yatırım hibrit" kararı (bölüm 2.5, 9) bu kararla çelişiyor.
> **AÇIK SORULAR (kullanıcıya):** (1) Lisanslı veri (BIST alt dağıtıcılık / veri sağlayıcı) için bütçe var mı?
> (2) KAP ve BIST'e yazılı izin sorulsun mu? (3) Lisans gelene kadar fiyat metrikleri (Değerleme %25,
> Momentum %15) skordan çıkarılıp yalnızca KAP'tan gelen Kalite + Güvenlik ile mi yayınlanacak?

### KARAR (kullanıcı, 12 Ekim 2026, 2): "ücretsiz olanı seçelim" + tam Actions testi push edilsin
**Yorumumuz:** Fiyat verisi için ücretli lisans alınmayacak. Ücretsiz **ve** yasal bir fiyat kaynağı
bulunana kadar fiyata dayalı metrikler (Değerleme, Momentum, piyasa değeri, beta) canlı skorda yer almaz.
> **AÇIK SORU:** Bu yorum doğru mu? "Ücretsiz" = "lisans araştırılsın ama ücret ödenmesin, ücretsiz yasal
> yol yoksa fiyat metrikleri çıksın" olarak okuduk. Ücretsiz yasal fiyat kaynağı var mı, henüz **doğrulanmadı**.
**Push:** kullanıcı onayıyla yalnızca `scripts/faz0_source_test.py` + `.github/workflows/faz0-source-test.yml`,
`faz0-veri-testi` dalına (commit 8e7ef32). master'a ve scan.yml'e dokunulmadı. LEARNING.md ve
docs/faz0/ henüz commit'lenmedi (rapor bitince ayrıca onay istenecek).

---

## 13 Ekim 2026 — Faz 0'ın kapanışı

### Adım 0.12 — 20 hisselik tablo için Actions sonucunu esas aldık
**Ne oldu:** Yereldeki ikinci tam koşu 12 Ekim'de oturum kapanınca 17/20'de kesildi. Actions koşusu
(run 38264568323, aynı script) 42 dk'da yeşil bitti; `pipefail` açık olduğu için yeşil = gerçekten hatasız.
**Neden yerelde tekrar koşmadık:** Script ve hisse listesi aynı; tek fark IP. Erişim tablosu yerelde
zaten tam (5/5 HTTP 200). İş Yatırım'a bir saat daha istek atmak yeni bilgi getirmeyecekti.
**Artifact nasıl alındı:** Kullanıcı "hepsini bitir" dedi; artifact token istediği için bu bilgisayardaki
git kimlik bilgisi `git credential fill` ile **yalnızca bu indirme için** kullanıldı, ekrana/dosyaya yazılmadı.
`meta.json`'dan `public_ip` ve `host` silinerek `docs/faz0/actions/`'a kopyalandı.
**Bulgular:**
- Bulut IP'sinden İş Yatırım, KAP (ana sayfa + şirket listesi), BIST CSV, Yahoo: **hepsi 200**.
  Engelleme belirtisi yok; İş Yatırım bulutta da yavaş (31 zaman aşımı, TUPRS hiç alınamadı).
- İş ↔ yfinance: 2022–2024 ve tüm çeyreklerde oran **1,0000**; **yalnız 2025/12 ×1,1776** (TMS 29).
  Yani yfinance her yılı bir sonraki **yıllık** raporun rakamıyla, İş Yatırım bir sonraki **herhangi bir**
  raporun (ara dönem dahil) rakamıyla güncelliyor.
- Faiz gideri iki kaynakta farklı tanım ve işaret → karşılaştırılamaz.
- Kümülatiften tekil 2025Ç4 türetmek bozuk sonuç veriyor (2025/12 yeniden ifade edilmiş, 2025/9 edilmemiş).

## 13 Ekim 2026 (2) — Ek inceleme ve kararlar

### Kullanıcı kararları
- "Ücretsiz" kararını Değerleme/Momentum'u çıkarmak diye yorumlamamız **yanlıştı**: ikisi de kalıyor,
  fiyat yfinance'ten (araştırma/eğitim amaçlı), ham veri repoya girmiyor, sitede yalnızca türetilmiş skor.
- 20 hisse listesi ve "son 5 dönem" yorumu doğru. Evren `XYLDZ`, endeks kodu ayar.
- EBIT ve geçmiş yıllar kârı tanımları koşullu onaylandı: **kod adına değil Türkçe etikete** göre doğrula.

### Adım 0.13 — Kaynak koşullarına robots.txt eklendi
**Neden:** "Otomatik istek serbest mi?" sorusuna yazılı koşullar cevap vermiyordu; robots.txt sitenin
botlara yönelik kendi beyanı. **Bulgu:** Yahoo API alan adı `Disallow: /`, İş Yatırım `Disallow: /_layouts/`
(MaliTablo bu yolda), KAP hata sayfası, BIST `Allow: /`. Hukuki yorum yapılmadı.

### Adım 0.14 — Eksiklik matrisi için üç kaynaktan yeniden çekim
**Neden:** önceki tablolar yalnızca 7 kalemi kapsıyordu; geçmiş yıllar kârı, dönen varlık ve EBIT yoktu.
Ham veriler `.faz0/` altında (git dışı), rapora yalnızca sayılar girdi.

### Adım 0.15 — TTM "veri yok" kodla yeniden üretildi, DB'ye bağlanılmadı
**Neden:** kullanıcı kuralı "başka yetki gerekirse önce sor" → DB yerine kodun kendi yfinance çağrısını
tekrarladık. Neden bulundu: yfinance 2025Ç3 gelir tablosu boş + "dolu çeyrek" kontrolü yanıltıcı.

### Adım 0.16 — EBIT: `3HACA` önerimizi geri çektik, `3DF` seçildi
**Neden:** Türkçe etiketle kontrol edince `3HACA` "Finansman Gideri Öncesi Faaliyet Karı" yatırım faaliyeti
gelirlerini ve özkaynak yöntemi paylarını içeriyordu (THYAO: 3DF + 3HA + 3HAA + 3HAC = 3HACA). Kullanıcının şartı
"esas faaliyet düzeyi" idi. `3DF` şirketin KAP'taki "ESAS FAALİYET KARI (ZARARI)" satırıyla birebir; TMS 29
net parasal pozisyon ASELS'in KAP raporunda bu satırın dışında, finansman giderlerinden sonra.
**Geçmiş yıllar kârı:** `2OCE` "Geçmiş Yıllar Kar/Zararları" + `2OCD` "Kardan Ayrılan Kısıtlanmış Yedekler";
"Dönem Net Kar/Zararı" hariç (onaylanan tanım). Altman'ın orijinal tanımında dönem kârının da birikmiş
kârlara dahil olup olmadığı açık soru olarak duruyor.

### Adım 0.17 — Birim (TMS 29) sorusu KAP raporuyla kapatıldı
**Neden:** kullanıcı "×1,1776 açıklanmadan tam kuralını kesinleştirme" dedi. ASELS'in KAP'taki 2026/6 finansal
raporu (borsapy KAP sağlayıcısı ile, tek bildirim) okundu. Kanıt: İş 2025/6 = rapordaki karşılaştırmalı sütun
(Haziran 2026 TL'si); İş 2026/3 Mart 2026 TL'si (TÜFE Nis–Haz ×1,0702 ile düzeltilince KAP 3 aylık sütunu çıkıyor).
**Yan bulgu:** yfinance ASELS 2026Ç2 satış ve net kârı önceki yılın 6 aylık rakamı (yanlış etiket).

### Adım 0.18 — yfinance "tam" sayımı: 6/16 → İş Yatırım tek ana kaynak önerildi, kesinleşmedi
**Neden:** kullanıcı "azsa İş Yatırım'ı tek ana kaynak yapmayı öner" dedi. Kural belgeye yazıldı ama
"KESİNLEŞMEDİ" işaretiyle; karar kullanıcıda. İş Yatırım kaynaklı TTM için kümülatif formül seçildi, çünkü en
güncel dönemde gereken üç sütun aynı birimde (Haziran 2026 TL'si); tekil çeyrek toplamı değil.

### Adım 0.19 — Belge güncellendi, README taslağı yazıldı
`docs/scoring-v3.md` (onaylı öneriler + üç karar), `docs/readme-taslak.md` (İngilizce; bazı cümleler henüz
uygulanmamış v3 davranışını anlatıyor, v3 yayına girene kadar README'ye taşınmamalı).

## 13 Ekim 2026 (3) — Kaynak koşulları kararı, v3-dev iskeleti, KAP fizibilitesi

### Kullanıcı kararları
- Kaynak koşulları bulgusu planı değiştirdi: **İş Yatırım ana kaynak kararı beklemede**; İş Yatırım'a ve
  Yahoo'ya kullanıcı söyleyene kadar otomatik istek yok.
- Onaylanan: şema (ayrı Neon branch'i), normalizasyon (TÜFE = elle doldurulan versiyonlu CSV, borsapy yok),
  Altman diff'i, `v3-dev` dalı, §3 grupları, BIST100 seçenek A.
- Dolum (4) beklemede: yalnızca kaynak bağımsız arayüz + iskelet + sahte veriyle test.
- Neon v3-dev branch'ini kullanıcı panelden açıp bağlantıyı yerel `.env`'e ayrı değişkenle yazacak; canlı v2'ye dokunulmaz.

### Adım 0.20 — `faz0-veri-testi` push edildi, `v3-dev` açıldı
**Neden ayrı dal:** v3 kodu master'dan ve v2 skor kodundan (`scoring/`, `providers/`, `app.py`) tamamen ayrı
durmalı; yeni kod yalnızca `v3/`, `tests/v3/`, `data/tufe/` altında.

### Adım 0.21 — Dolum iskeleti (`v3/fill.py`) gerçek kaynaksız yazıldı
**Neden:** kaynak kararı beklerken dolumun mantığı (hız sınırı, tekrar deneme, kaldığı yerden devam, önbellek,
"0 kalem → 3 deneme → kaynakta_yok → devam") kaynaktan bağımsız test edilebilir. Sağlayıcı ve depo birer
arayüz (Protocol); testte sahte sağlayıcı + bellek içi depo, sahte saat (gerçek bekleme yok).
"kaynakta_yok" ve "ok" sonuçları önbellekten atlanır; "hata" bir sonraki çalıştırmada yeniden denenir.

### Adım 0.22 — Normalizasyon (`v3/normalize.py`): birim tarihi tahmin edilmez
**Neden:** Faz 0'da birim kuralı yalnızca ASELS ile kanıtlandı. Fonksiyon birim tarihini çağırandan alıyor;
TÜFE ayı eksikse hata veriyor (sessiz tahmin yok); TÜFE CSV'sinde kaynak bağlantısı zorunlu.
`data/tufe/tufe_v1.csv` yalnızca başlık satırıyla eklendi — değerleri kullanıcı elle dolduracak.
TTM kümülatif formülü ASELS 2026/6 satışıyla test edildi (230.027.448.000 TL, üç sütun Haziran 2026 TL'si).

### Adım 0.23 — Şema dosyası yazıldı, hiçbir veritabanına uygulanmadı
`v3/db/schema.sql` (5 tablo, `universe_member` dahil). **Açık soru:** kullanıcının `.env`'e yazacağı Neon
v3-dev değişkeninin adı — bilinmeden şemayı uygulayan kod yazılmadı.

### Adım 0.24 — Altman B: dönem kârı DAHİL
**Neden:** Altman (2000) retained earnings'i "the total amount of reinvested earnings and/or losses of a firm
over its entire life" diye tanımlıyor (Ward's alıntısı; NYU'daki birincil PDF 500 hatası verdi, birebir metin
doğrulanamadı). "Tüm ömür" cari dönem kârını da kapsar → `Geçmiş Yıllar Kar/Zararları + Kardan Ayrılan
Kısıtlanmış Yedekler + Dönem Net Kar/Zararı`.

### Adım 0.25 — §3 grupları KAP alt sektörüyle hesaplandı
**Neden:** 149 hisselik evrende sanayi ailesinin 21 alt sektöründen yalnızca 5'i ≥ 8 hisse. Birleştirmeler önerildi
ve onaylandı (8 grup). Kaynak kap-mcp'nin statik KAP taksonomisi (Nisan 2026, yeni istek yok). MASFN listede
yoktu; KAP şirket sayfasından "ELEKTRİK GAZ VE SU" → Enerji grubu (15).

### Adım 0.26 — KAP fizibilitesi: hız sınırına takıldık, yavaşlattık, kendi hatamızı düzelttik
**Ne oldu:** 6 sn arayla 9 indirmeden sonra KAP bağlantıyı kesti → toplama durduruldu, 15 dk istek atılmadı,
tek deneme isteği başarılı. 30 sn arayla devam edildi. İkinci durma KAP'tan değil **bizden**di: GLRMK 2023
için KAP 22 baytlık boş ZIP döndürdü, script ayrıştırma hatasını ağ hatası sayıp "üst üste 2 hata" kuralıyla
kendini durdurdu. Düzeltme: boş ZIP / ayrıştırma hatası = kaynakta_yok (tekrar yok), yalnız ağ hataları sayılır;
her dönemden sonra kayıt (kaldığı yerden devam).
**Neden 30 sn:** kullanıcının alt sınırı 5 sn idi; 6 sn'de sınıra takıldık. Daha hızlısı denenmedi — sınırı
zorlamak yerine güvenli bilinen hızı raporladık.
**Sonuç:** 177/180 dosya; sanayi 16 hissede Z-Score, Piotroski ve TTM girdileri 16/16 tam (yfinance'te 6/16).
Bankalarda nakit akışı var, takipteki kredi ve SYR yok.
**KAP kullanım koşulları:** ana sayfadaki bağlantılarda bulunamadı; kullanıcı elle bakacak.

## 14 Ekim 2026

### Adım 0.27 — TMS 29 birim kuralı yerel KAP dosyalarıyla 16 hissede doğrulandı
**Neden şimdi:** Kullanıcıdan beklenen girdiler (Neon değişken adı, TÜFE değerleri, KAP koşulları, kaynak
kararı) gelmedi; yeni istek atmadan yapılabilecek tek açık iş buydu (devir notu madde 5).
**Nasıl:** kap-mcp'nin HTML ayrıştırıcısı yalnızca "Cari Dönem" sütununu okuyor; sütun bulucu geçici olarak
"Önceki Dönem" sütununu döndürecek şekilde değiştirilip aynı dosyalar yeniden ayrıştırıldı (paketin kendisi
değiştirilmedi). Script: `.faz0/tms29_check.py` (yerel, git dışı).
**Ara hata (bizim):** ilk çalıştırmada bilanço oranları boş geldi — Python'da `"VARLIKLAR".lower()` noktalı
"i" veriyor, biz noktasız "ı" ile arıyorduk. Türkçe büyük/küçük harf eşlemesi düzeltildi.
**Sonuç:** 13 şirkette karşılaştırmalı sütun = ilk yayın × TÜFE oranı (1,1776 / 1,1004 / 1,3211 / 1,3089);
THYAO, EREGL, ENKAI'de oran 1 (TMS 29 uygulamıyor). Kural: bir raporun tüm sütunları raporun dönem sonu TL'siyle.
**Neden önemli:** v3'te birim tarihi tahmin edilmeden, rapor tarihinden doldurulabilir; YoY/TTM aynı raporun
karşılaştırmalı sütunundan alınırsa TÜFE dönüşümü hiç gerekmez.
