# Faz 0 — Devir Notu

Oturum: 12 Ekim 2026. Sonraki oturum bu dosyayı, ardından `docs/faz0/faz0-raporu.md` ve
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
| `docs/faz0/local/` | **hayır** | 2. tam koşunun çıktısı; commit sırasında koşu sürüyordu. İçindeki `meta.json` yerel genel IP adresini içeriyor → commit'lemeden önce o alan temizlenmeli. |
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

1. **Adım 1 — 20 hisselik düzeltilmiş koşu** (`docs/faz0/local/`, log `.faz0/local_run2.log`):
   commit anında 11/20'deydi. Bitince `summary.md`'deki eksik oran ve fark tablosu rapora (bölüm 1.3)
   işlenmeli. Koşu yarıda kesildiyse: `.venv/Scripts/python scripts/faz0_source_test.py --out docs/faz0/local`
   (~40-60 dk; İş Yatırım yavaşsa uzar). Yalnız özet: `--summarize-only`.
2. **Adım 3 — Actions sonucu:** run 38264568323 (`faz0-veri-testi`). Sonuç Actions'ın Summary
   sayfasında ve `faz0-actions-<run_id>` artifact'ında. Log/artifact token olmadan inmiyor (403):
   kullanıcı Summary'yi iletmeli ya da indirme için izin vermeli. Sonuç rapora (bölüm 3) ve
   bölüm 12 "Actions IP erişimi" satırına işlenmeli.
3. **Doğrulanamayanlar:** XYLDZ'nin 271 → 149 düşüş nedeni; ağustos-ekim taramalarının Python
   tarafında neden 4 sn'de çöktüğü; KAP'tan otomatik çekim ve yeniden yayının yasal durumu;
   ücretsiz yasal fiyat kaynağı var mı; THYAO 2023/12 istisnası; GARAN KAP 1000× okuma;
   2025/6 ↔ 2026/6 aynı bazda mı; pykap ve kap-mcp'nin bugün çalışıp çalışmadığı.
4. **Kullanıcı teyidi bekleyen sorular:** "ücretsiz" yorumu; 20 hisse seçimi; "son 5 dönem" yorumu.

## Sonraki oturum ilk olarak ne yapmalı

1. `git status` + `git log faz0-veri-testi` ile durumu doğrula; `docs/faz0/local/summary.md` var mı bak.
2. Actions run 38264568323'ün sonucunu al (kullanıcıdan Summary/zip ya da izin) ve rapora işle.
3. Yerel koşu tamamlandıysa eksik oran/fark tablosunu rapora işle; `meta.json`'daki `public_ip`'yi
   temizlemeden `docs/faz0/local/`'i commit'leme. `.faz0/`'ı `.gitignore`'a ekle.
4. Kullanıcıya üç teyit sorusunu sor ("ücretsiz" yorumu, hisse seçimi, dönem yorumu).
5. **Faz 1'e geçmeden önce** yasal kaynak sorusunu kapat: KAP (MKK) ve Borsa İstanbul'a yazılı
   soru taslağı hazırla (KAP verisinden türetilmiş metrik yayınlama; gün sonu fiyatı / evren listesi yayını).
   Bu cevap gelmeden v3 veri katmanı tasarlanmamalı.
6. Belge değişiklik önerilerini (rapor bölüm 6) kullanıcıyla tek tek geçip onaylananları belgeye işle.
7. `scan.yml`'deki pipefail hatası canlıyı etkiliyor; Faz 0 kapsamı dışında ama kullanıcıya ayrı bir
   düzeltme olarak önerilmeli (onaysız değiştirme).
