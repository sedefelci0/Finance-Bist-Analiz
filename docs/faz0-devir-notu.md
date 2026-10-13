# Faz 0 — Devir Notu

Oturum: 12 Ekim 2026 (13 Ekim'de Actions sonuçlarıyla güncellendi). Sonraki oturum bu dosyayı, ardından `docs/faz0/faz0-raporu.md` ve
`LEARNING.md`'yi okuyarak başlamalı.

## Ne yaptık

1. `docs/scoring-v3.md` (Alpha Score v3 karar belgesi) okundu. **Belge değiştirilmedi.**
2. Üç kaynağın (yfinance, isyatirimhisse, borsapy) ve sitelerin (Yahoo, İş Yatırım, Borsa İstanbul,
   KAP) kullanım koşulları okundu.
3. İş Yatırım `MaliTablo` uç noktasının ham cevabı incelendi; sanayi, banka, sigorta kalem kodları çıkarıldı.
4. 20 hisse × 7 kalem × 3 kaynak karşılaştırma script'i yazıldı (`scripts/faz0_source_test.py`),
   3 hisseyle smoke test, 20 hisseyle iki tam koşu (ilki script hatası nedeniyle atıldı).
5. 5 hissede İş Yatırım ↔ KAP karşılaştırıldı; farkın TMS 29 (TÜFE) yeniden ifadesi olduğu kanıtlandı.
6. Evren sorunu (290 vs 149) kod, GitHub Actions public API, veritabanı (yalnızca okuma) ve resmi CSV ile çözüldü.
7. pykap ve kap-mcp kurulup içerikleri incelendi (çalıştırılmadı).
8. Actions erişim testi workflow'u yazıldı ve `faz0-veri-testi` dalına push edildi.
9. Bölüm 12 soruları cevaplandı, belge için 10 değişiklik önerisi yazıldı.

## Verilen kararlar ve nedenleri

| Karar | Kimin | Neden |
|---|---|---|
| Site herkese açık olacak, yalnızca yasal kaynak | Kullanıcı | — |
| Fiyat verisi için ücretsiz olanı seç | Kullanıcı | Yorumumuz: ücretli lisans yok; ücretsiz yasal fiyat kaynağı bulunana kadar fiyat metrikleri canlı skorda yok. **Bu yorum kullanıcıya teyit ettirilmedi.** |
| Araştırma koşusu bitsin, rapora girsin | Kullanıcı | Veri kalitesi bulguları ileride kaynak seçerken ölçüt olur. |
| Actions testi tam haliyle push edilsin | Kullanıcı | — |
| Paketler gitignore'daki `.venv`'e | Biz | `requirements.txt` ve global Python kirlenmesin. |
| İstekler arası ≥ 3 sn | Biz | Resmi istek sınırı yok; muhafazakâr seçim. |
| 20 hissenin 10'u belgeden, 2 GYO + 8 sektör bizim seçimimiz | Biz | Görev isim vermiyordu. **Kullanıcı teyidi bekliyor.** |
| "Son 5 dönem" = son 5 çeyrek **ve** son 5 yıl | Biz | Belirsizdi. **Kullanıcı teyidi bekliyor.** |
| Banka/sigortada önce `UFRS_K` (konsolide) | Biz | `UFRS` solo çıkıyor; yfinance konsolide veriyor (GARAN ile doğrulandı). |
| Kapsama oranı aileye göre ayrı | Biz | Bankada "satış yok" eksiklik değil, uygulanamaz. |
| İlk 20 hisselik koşu silinip yeniden koşuldu | Biz | Zaman aşımı "veri yok" sanılmıştı + borsapy borç satırı iki kez seçilmişti (ikisi de bizim hatamız). |
| Actions workflow'u ayrı dosya, ayrı dal, secret yok, pipefail açık | Biz | `scan.yml`'ye dokunmamak, aynı sessiz-yeşil hatayı tekrarlamamak. |
| DB'ye yalnızca `SET TRANSACTION READ ONLY` ile sorgu | Biz | Actions log'ları 403; 149'un nerede oluştuğunu görmenin tek doğrudan yolu. |

## Oluşan dosyalar

| Dosya | Commit'te mi | Not |
|---|---|---|
| `LEARNING.md` | evet | Her adımın "neden böyle yaptık" kaydı + açık sorular |
| `docs/faz0-devir-notu.md` | evet | Bu dosya |
| `docs/faz0/faz0-raporu.md` | evet | Faz 0 raporu (1. ve 3. adım sonuçları eksik) |
| `docs/faz0/kap_vs_isyatirim.md` / `.csv` | evet | Adım 2 ayrıntısı |
| `scripts/faz0_source_test.py` | evet (8e7ef32) | Kaynak testi script'i |
| `.github/workflows/faz0-source-test.yml` | evet (8e7ef32) | Actions erişim testi |
| `docs/faz0/actions/` | evet | Actions koşusunun 20 hisselik sonucu (artifact'tan; `public_ip` ve `host` silindi) |
| `docs/faz0/local/` | evet (yalnız `connectivity.csv`) | Yerel erişim tablosu; ikinci tam koşu 17/20'de kesildi |
| `.faz0/` | **hayır** | Ham deneme çıktıları (probe, smoke, CSV kopyası, KAP JSON, koşu log'ları). Repo'ya girmemeli; `.gitignore`'a eklenmesi önerilir. |
| `.venv/` | hayır (gitignore) | yfinance 1.7.0, isyatirimhisse 5.0.1, borsapy 0.11.0, pykap 0.2.0, kap-mcp 0.1.0, tabulate, sqlalchemy, psycopg2 |

## Sonuçlar (özet — ayrıntı raporda)

- **Kaynaklar:** yfinance, isyatirimhisse, borsapy herkese açık sitede kullanılamaz (koşullar).
  borsapy finansalları da İş Yatırım'dan → gerçekte iki bağımsız kaynak.
- **Fiyat verisi:** Borsa İstanbul gecikmeli veri dahil web yayınını lisansa bağlıyor → Değerleme
  ve Momentum pillar'ları, piyasa değeri, beta etkileniyor.
- **TMS 29:** İş Yatırım eski yıl sonlarını TÜFE ile yeniden ifade ediyor (×1,1776 / 1,3089 / 1,4438),
  KAP özet sayfası ilk yayımlanan rakamı veriyor. 2026/6 her ikisinde birebir.
- **Bankalar:** `UFRS` solo, `UFRS_K` konsolide; nakit akışı yok, SYR yok, takipteki kredi 0.
- **Para birimi:** THYAO ve ENKAI yfinance tabloları USD.
- **Evren:** CSV'de XYLDZ bugün 149 hisse; Actions sessizce eski listeye düşmüyor. "~290" büyük ihtimalle
  DB'deki 291 farklı hisse. XYLDZ Yıldız Pazar'ın tamamı değil.
- **Canlı tarama hatası:** 14 Ağustos–10 Ekim arası ~24 zamanlanmış koşu yeşil göründü ama DB'ye
  hiç yazmadı (`python | tee`, pipefail yok). 11 ve 12 Ekim koşuları çalıştı (148 hisse).
- **KAP sektörü:** holding/GYO/sigorta/banka aynı ana sektörde; SISE "Holdingler" altında.

## Yarım kalanlar

**Faz 0'ın 6 adımı tamamlandı (13 Ekim).** 1. ve 3. adımın sonuçları Actions koşusundan
(run 38264568323) alınıp rapora işlendi; veriler `docs/faz0/actions/`. Yereldeki ikinci tam koşu
12 Ekim'de oturum kapanınca 17/20'de kesildi; aynı test bulutta tamamlandığı için tekrarlanmadı
(`docs/faz0/local/` yalnızca yerel erişim tablosunu içerir — IP içermez).

Açık kalanlar:
1. **Doğrulanamayanlar:** XYLDZ'nin 271 → 149 düşüş nedeni; ağustos-ekim taramalarının Python
   tarafında neden 4 sn'de çöktüğü (artık token ile log indirilebilir, bkz. aşağıda); KAP'tan otomatik
   çekim ve yeniden yayının yasal durumu; ücretsiz yasal fiyat kaynağı var mı; THYAO 2023/12 istisnası;
   GARAN KAP 1000× okuma; 2025/6 ↔ 2026/6 aynı bazda mı; pykap ve kap-mcp'nin bugün çalışıp çalışmadığı;
   KAP'ın JS ile yüklenen finansal tablo sayfasına bulut IP'sinden erişim.
2. **Kullanıcı teyidi bekleyen sorular:** "ücretsiz" yorumu; 20 hisse seçimi; "son 5 dönem" yorumu.
3. **Script'te bilinen kusur:** sigorta "finansal borç" eşlemesi borsapy tarafında yalnız ilk satırı alıyor
   (AGESA/ANHYT borç farkı bundan). Faz 0 sonucunu değiştirmiyor.

## Sonraki oturum ilk olarak ne yapmalı

1. `git pull` + `git switch v3-dev` (v3 iskeleti burada; `faz0-veri-testi` Faz 0'ın kendisi).
2. Oku: bu not, `docs/faz0/faz0-raporu.md` bölüm 7–8, `LEARNING.md` 0.20–0.26.
3. **Kullanıcı kararı bekleyenler:** ana finansal kaynak (aday KAP; İş Yatırım ve Yahoo'ya otomatik istek
   YASAK, kullanıcı söyleyene kadar), fiyat kaynağı, KAP kullanım koşulları (kullanıcı elle bakacak).
4. Kullanıcıdan: Neon v3-dev branch bağlantı değişkeninin adı; `data/tufe/tufe_v1.csv` değerleri.
5. Yeni istek atmadan yapılabilecek: KAP dosyalarındaki karşılaştırmalı sütunlarla TMS 29 birim kuralını
   10 hissede doğrula (dosyalar yalnızca bu bilgisayarda `.faz0/kap_fz/raw/`, repoda yok).
6. `scan.yml`'deki pipefail hatası canlıyı etkiliyor; ayrı düzeltme olarak öner (onaysız değiştirme).

---

## Nasıl yaptık (başka bilgisayarda tekrar üretmek için)

### Kurulum
```bash
git clone https://github.com/sedefelci0/Finance-Bist-Analiz.git && cd Finance-Bist-Analiz
git switch faz0-veri-testi
python -m venv .venv            # .venv gitignore'da
# Windows: .venv\Scripts\python   |  Linux/Mac: .venv/bin/python
.venv/Scripts/python -m pip install yfinance isyatirimhisse borsapy pandas tabulate requests openpyxl
# yalnızca DB sorgusu ve KAP karşılaştırması için:
.venv/Scripts/python -m pip install sqlalchemy psycopg2-binary python-dotenv playwright beautifulsoup4
.venv/Scripts/python -m playwright install chromium
```
Kullanılan sürümler: yfinance 1.7.0, isyatirimhisse 5.0.1, borsapy 0.11.0 (Python 3.14 yerelde, 3.12 Actions'ta).
DB için `.env` gerekir — **repoda yok**, ev bilgisayarına elle kopyalanmalı (`.env.example`'a bak).

### Adım 1 — kaynak testi
```bash
.venv/Scripts/python scripts/faz0_source_test.py --out docs/faz0/local      # ~40-60 dk
.venv/Scripts/python scripts/faz0_source_test.py --out docs/faz0/local --summarize-only
.venv/Scripts/python scripts/faz0_source_test.py --out docs/faz0/deneme --tickers THYAO,GARAN,AGESA  # hızlı deneme
```
Çıktılar: `connectivity.csv`, `raw_values.csv`, `coverage.csv`, `diffs.csv`, `per_ticker.csv`, `summary.md`, `meta.json`.
`meta.json` makinenin genel IP'sini içerir → commit'lemeden önce `public_ip` alanını sil.

**12 Ekim'deki 2. tam koşu bu (iş) bilgisayarında, push anında 14/20'deydi; çıktısı GitHub'a gitmedi.**
Evde ya yeniden koş ya da aynı testin Actions sonucunu (aşağıda) kullan.

### İş Yatırım ham cevabına bakmak (kalem kodları)
```python
import requests
u = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
p = dict(companyCode="THYAO", exchange="TRY", financialGroup="XI_29",   # banka/sigorta: UFRS_K (konsolide) / UFRS (solo)
         year1=2026, period1=6, year2=2026, period2=3, year3=2025, period3=12, year4=2025, period4=6)  # EN AZ 4 dönem!
for it in requests.get(u, params=p, timeout=30).json()["value"]:
    print(it["itemCode"], it["itemDescTr"], it["value1"], it["value2"], it["value3"], it["value4"])
```

### Adım 2 — İş Yatırım ↔ KAP
KAP tarafı projedeki `providers/kap_provider.fetch_all_periods_financials(ticker)` (Playwright) ile okundu;
İş tarafı yukarıdaki istekle `[(2026,6),(2025,12),(2024,12),(2023,12)]` dönemleri için. Kalemler:
sanayi `1BL` varlık, `3C` satış, `3L` toplam / `3Z` ana ortaklık net kâr, `2O` ana ortaklık / `2N` toplam özkaynak;
banka (`UFRS_K`) `1Z`, `3Z`, `2O`. Oran = |İş − KAP| / |KAP|. Sonuç: `docs/faz0/kap_vs_isyatirim.csv`.
TÜFE kontrolü: `borsapy.Inflation().tufe()` aylık değerlerinin çarpımı.

### Adım 3 — Actions sonucu
- Workflow: `.github/workflows/faz0-source-test.yml`; `faz0-veri-testi` dalına script/workflow değişikliği push'u
  ya da (workflow master'a alınırsa) Actions sekmesinden "Run workflow" tetikler.
- 12 Ekim koşusu: https://github.com/sedefelci0/Finance-Bist-Analiz/actions/runs/38264568323
  → **Summary** sekmesinde özet tablo, altta `faz0-actions-<run_id>` artifact zip'i (giriş yapmış kullanıcı indirebilir).
  13 Ekim'de API ile şöyle indirildi (token ekrana yazdırılmadan, kayıtlı git kimlik bilgisiyle):
  `TOKEN=$(printf "protocol=https
host=github.com

" | git credential fill | sed -n 's/^password=//p')`
  ardından `curl -L -H "Authorization: Bearer $TOKEN" -o artifact.zip https://api.github.com/repos/sedefelci0/Finance-Bist-Analiz/actions/artifacts/<artifact_id>/zip`.
  Aynı yolla job log'u: `.../actions/jobs/<job_id>/logs` (ağustos-ekim taramalarının 4 sn'de neden çöktüğü buradan bakılabilir).
- Durum sorgusu (token gerekmez):
  `curl -s https://api.github.com/repos/sedefelci0/Finance-Bist-Analiz/actions/runs/38264568323/jobs`

### Adım 4 — evren
- CSV: `https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv` (`;` ayraçlı, 3. sütun endeks kodu; XYLDZ sayıldı).
- Actions koşu geçmişi ve adım süreleri: `https://api.github.com/repos/sedefelci0/Finance-Bist-Analiz/actions/runs?per_page=40`
  ve `.../actions/runs/<id>/jobs` (token gerekmez; log indirmek 403).
- DB (yalnızca okuma, `.env` ile):
```python
from dotenv import load_dotenv; load_dotenv()
from db.connection import get_engine; from sqlalchemy import text
with get_engine().connect() as c:
    c.execute(text("SET TRANSACTION READ ONLY"))
    for r in c.execute(text("select date(created_at), count(distinct ticker) from pillar_scores group by 1 order by 1 desc")): print(r)
```

### Adım 5 — pykap / kap-mcp
`pip install pykap kap-mcp` → `site-packages/kap/data/bist_oid_master.json` (ticker → sector_group, alt_sektor,
parser_family) ve `sector_taxonomy.json` incelendi. Sunucu olarak çalıştırılmadı.

### Push durumu
`faz0-veri-testi` dalı GitHub'da (kullanıcı onayıyla push edildi, 12 Ekim). master'a merge edilmedi; PR açılmadı.
