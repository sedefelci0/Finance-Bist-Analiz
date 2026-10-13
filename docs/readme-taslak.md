# README draft — sections for BIST Alpha Score

> Draft (13 October 2026). Not yet merged into `README.md`. Wording about third-party terms
> quotes or paraphrases the providers' own texts; it is not legal advice or interpretation.

## Data sources and terms of use

BIST Alpha Score shows **derived scores only**. The site does not display or redistribute raw
financial statements, raw price series, or index constituent files. Raw provider data is not
stored in this repository.

| Source | What we use it for | What the provider's own text says |
|---|---|---|
| **Yahoo Finance via `yfinance`** | Daily prices (momentum, valuation multiples); financial statements when complete and reported in TRY | The `yfinance` project states it is "intended for research and educational purposes" and that "the Yahoo! finance API is intended for personal use only", and refers users to Yahoo's terms. Yahoo's Terms of Service restrict automated access ("access or collect data … using any automated means … without our express, prior permission") and commercial reuse/redistribution. `query1.finance.yahoo.com/robots.txt` disallows all paths for all user agents. |
| **İş Yatırım (`MaliTablo` endpoint, via direct HTTP)** | Financial statements when Yahoo data is incomplete or not in TRY | The İş Yatırım website states that all copyrights of its content belong to İş Yatırım Menkul Değerler A.Ş., and that "all copyrights of data generated in BIST markets belong to BIST and these data cannot be republished". A dedicated terms-of-use page could not be found. `isyatirim.com.tr/robots.txt` disallows `/_layouts/`, the path under which the endpoint sits. The community packages `isyatirimhisse` and `borsapy` describe themselves as "for personal use only". |
| **KAP (Public Disclosure Platform)** | Cross-checking figures; company sector classification | KAP disclosures are published free of charge on kap.org.tr. We could not find a published terms-of-use text covering automated access or reuse; this is unverified. |
| **Borsa İstanbul index file (`hisse_endeks_ds.csv`)** | Defining the stock universe | Borsa İstanbul's copyright notice says site content may not be copied, implemented or distributed, in part or in whole, without written permission. Borsa İstanbul's FAQ states that distributing delayed data requires a data distribution licence. |
| **TCMB inflation series** | Inflation adjustment checks (TMS 29) | — |

Requests are rate-limited (at least 3 seconds between calls), and İş Yatırım statements are
fetched once per new reporting period and cached, not re-downloaded on every scan.

**Your responsibility:** if you run this code yourself, review each provider's current terms.
Nothing here grants you any right to the underlying data.

## Limitations

- **Not investment advice.** The score summarises past financial statements and price trends.
  It is a filter, not a forecast.
- **Weights are untested.** Quality 30% / Safety 30% / Valuation 25% / Momentum 15% are this
  project's own design choice, inspired by the literature but not backtested. Backtesting is planned.
- **Inflation accounting (TMS 29).** Turkish companies restate prior periods for inflation.
  Different sources show the same period in different purchasing-power units (e.g. İş Yatırım's
  2025 year-end figures are expressed in June 2026 lira, Yahoo's in December 2025 lira — a factor
  of 1.1776). Growth and year-over-year figures are sensitive to this.
- **Data gaps.** Yahoo is missing some quarters (e.g. Q3 2025 income statements for several
  companies), which can make trailing-twelve-month figures unavailable. Missing metrics are
  never treated as zero; their weight is redistributed or the pillar is marked "insufficient data".
- **Currency.** Some companies report to Yahoo in USD (e.g. THYAO, ENKAI); for these, multiples
  are recomputed from TRY price and TRY financial statements.
- **Banks and insurers** use different statement formats. Some bank metrics (capital adequacy
  ratio, non-performing loans) are not available in the sources used and are shown as "not applicable".
- **Sector groups** are derived from KAP's sector taxonomy, which places holdings, REITs, banks
  and insurers under the same main sector; some companies are reclassified manually.
- **Universe.** The universe is built from Borsa İstanbul's index constituents file; its
  definition (which index code) affects which companies are scored.

## AI assistance

This project was developed with the help of **Claude Code** (Anthropic's AI coding assistant),
used for code, data-source testing and documentation drafts. Design decisions and the
verification of results are the author's own. Each step, including what was tried and why a
decision was made, is recorded in [`LEARNING.md`](LEARNING.md).
