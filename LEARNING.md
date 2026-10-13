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
