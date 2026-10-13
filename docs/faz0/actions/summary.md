# Faz 0 kaynak testi — 2026-10-12 15:22

## Erişim

| check               | url                                                                                   |   status |   bytes |   seconds | content_type                    |   csv_rows |   csv_unique_E |   csv_XYLDZ |   csv_XUTUM |   items |
|:--------------------|:--------------------------------------------------------------------------------------|---------:|--------:|----------:|:--------------------------------|-----------:|---------------:|------------:|------------:|--------:|
| borsa_istanbul_csv  | https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv                               |      200 |  433215 |      1.98 | application/octet-stream        |       5782 |            591 |         149 |         582 |     nan |
| isyatirim_malitablo | https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo |      200 |   28264 |      1.29 | application/json; charset=utf-8 |        nan |            nan |         nan |         nan |     147 |
| kap_home            | https://www.kap.org.tr/tr/                                                            |      200 |  163124 |      1.48 | text/html; charset=utf-8        |        nan |            nan |         nan |         nan |     nan |
| kap_company_list    | https://www.kap.org.tr/tr/bist-sirketler                                              |      200 | 1540724 |      1.57 | text/html; charset=utf-8        |        nan |            nan |         nan |         nan |     nan |
| yahoo_chart         | https://query1.finance.yahoo.com/v8/finance/chart/THYAO.IS?range=5d&interval=1d       |      200 |    1478 |      0.19 | application/json;charset=utf-8  |        nan |            nan |         nan |         nan |     nan |

## Eksik oranı (0 = tam, 1 = hiç yok)

| aile     | kalem            | donem   |   borsapy |   isyatirimhisse |   yfinance |
|:---------|:-----------------|:--------|----------:|-----------------:|-----------:|
| finansal | equity           | ceyrek  |      0.2  |            0     |      0.15  |
| finansal | equity           | yillik  |      0.2  |            0     |      0.2   |
| finansal | financial_debt   | ceyrek  |      0.6  |            0.5   |      0.15  |
| finansal | financial_debt   | yillik  |      0.6  |            0.5   |      0.2   |
| finansal | interest_expense | ceyrek  |      0.6  |            0.5   |      0.6   |
| finansal | interest_expense | yillik  |      0.6  |            0.5   |      0.6   |
| finansal | net_income       | ceyrek  |      0.2  |            0     |      0.15  |
| finansal | net_income       | yillik  |      0.2  |            0     |      0.2   |
| finansal | ocf              | ceyrek  |      1    |            1     |      0.5   |
| finansal | ocf              | yillik  |      1    |            1     |      0.55  |
| finansal | revenue          | ceyrek  |      1    |            1     |      0.15  |
| finansal | revenue          | yillik  |      1    |            1     |      0.2   |
| finansal | total_assets     | ceyrek  |      0.2  |            0     |      0.15  |
| finansal | total_assets     | yillik  |      0.2  |            0     |      0.2   |
| sanayi   | equity           | ceyrek  |      0.25 |            0.1   |      0.062 |
| sanayi   | equity           | yillik  |      0.25 |            0.113 |      0.2   |
| sanayi   | financial_debt   | ceyrek  |      0.25 |            0.1   |      0.062 |
| sanayi   | financial_debt   | yillik  |      0.25 |            0.113 |      0.2   |
| sanayi   | interest_expense | ceyrek  |      0.25 |            0.1   |      0.062 |
| sanayi   | interest_expense | yillik  |      0.25 |            0.113 |      0.213 |
| sanayi   | net_income       | ceyrek  |      0.25 |            0.1   |      0.062 |
| sanayi   | net_income       | yillik  |      0.25 |            0.113 |      0.2   |
| sanayi   | ocf              | ceyrek  |      0.25 |            0.1   |      0.012 |
| sanayi   | ocf              | yillik  |      0.25 |            0.113 |      0.2   |
| sanayi   | revenue          | ceyrek  |      0.25 |            0.1   |      0.062 |
| sanayi   | revenue          | yillik  |      0.25 |            0.113 |      0.2   |
| sanayi   | total_assets     | ceyrek  |      0.25 |            0.1   |      0.062 |
| sanayi   | total_assets     | yillik  |      0.25 |            0.113 |      0.2   |

## Hisse bazında

| ticker   | aile       | isy_grup   | yf_currency   | yf_financialCurrency   |   yf_sharesOutstanding | son_donem_isy   | son_donem_borsapy   | son_donem_yf_ceyrek   | son_donem_yf_yillik   |
|:---------|:-----------|:-----------|:--------------|:-----------------------|-----------------------:|:----------------|:--------------------|:----------------------|:----------------------|
| AGESA    | insurance  | UFRS_K     | TRY           | TRY                    |              180000000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| AKBNK    | bank       | UFRS_K     | TRY           | TRY                    |             5200000000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| ANHYT    | insurance  | UFRS_K     | TRY           | TRY                    |              430000000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| ASELS    | industrial | XI_29      | TRY           | TRY                    |             4560000000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| BIMAS    | industrial | XI_29      | TRY           | TRY                    |             1185780000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| EKGYO    | industrial | XI_29      | TRY           | TRY                    |             3661120138 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| ENKAI    | industrial | XI_29      | TRY           | USD                    |             5862743582 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| EREGL    | industrial | XI_29      | TRY           | TRY                    |             6721875999 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| FROTO    | industrial | XI_29      | TRY           | TRY                    |             3509100000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| GARAN    | bank       | UFRS_K     | TRY           | TRY                    |             4200000000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| GLRMK    | industrial | XI_29      | TRY           | nan                    |              322600000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| ISGYO    | industrial | XI_29      | TRY           | TRY                    |              958750000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| KCHOL    | industrial | XI_29      | TRY           | TRY                    |             2535007575 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| SAHOL    | industrial | XI_29      | TRY           | TRY                    |             2067834969 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| SISE     | industrial | XI_29      | TRY           | TRY                    |             2992436056 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| TCELL    | industrial | XI_29      | TRY           | TRY                    |             2176442555 | 2026/6          | 2026/6              | 2026/6                | 2024/12               |
| THYAO    | industrial | XI_29      | TRY           | USD                    |             1372283353 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| TMSN     | industrial | XI_29      | TRY           | TRY                    |              115000000 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |
| TUPRS    | unknown    |            | TRY           | TRY                    |             1926795598 | -               | -                   | 2026/6                | 2025/12               |
| ULKER    | industrial | XI_29      | TRY           | TRY                    |              369275855 | 2026/6          | 2026/6              | 2026/6                | 2025/12               |

## Kaynaklar arası fark (göreli)

| karsilastirma             | kalem            |   n |   medyan_fark |   fark_gt_2pct |
|:--------------------------|:-----------------|----:|--------------:|---------------:|
| isy_vs_yfinance_ceyrek    | equity           |  84 |       0       |             21 |
| isy_vs_yfinance_ceyrek    | financial_debt   |  76 |       0       |             26 |
| isy_vs_yfinance_ceyrek    | interest_expense |  75 |       2.2702  |             67 |
| isy_vs_yfinance_ceyrek    | net_income       |  84 |       0.05145 |             50 |
| isy_vs_yfinance_ceyrek    | ocf              |  71 |       0       |             30 |
| isy_vs_yfinance_ceyrek    | revenue          |  67 |       0.2457  |             53 |
| isy_vs_yfinance_ceyrek    | total_assets     |  84 |       0       |             23 |
| isy_vs_yfinance_yillik    | equity           |  72 |       0       |             22 |
| isy_vs_yfinance_yillik    | financial_debt   |  64 |       0       |             26 |
| isy_vs_yfinance_yillik    | interest_expense |  63 |       2.7845  |             55 |
| isy_vs_yfinance_yillik    | net_income       |  72 |       0       |             25 |
| isy_vs_yfinance_yillik    | ocf              |  56 |       0.05865 |             29 |
| isy_vs_yfinance_yillik    | revenue          |  56 |       0.1776  |             32 |
| isy_vs_yfinance_yillik    | total_assets     |  72 |       0       |             22 |
| isyatirimhisse_vs_borsapy | equity           | 128 |       0       |              0 |
| isyatirimhisse_vs_borsapy | financial_debt   | 114 |       0       |             14 |
| isyatirimhisse_vs_borsapy | interest_expense | 114 |       0       |              0 |
| isyatirimhisse_vs_borsapy | net_income       | 128 |       0       |              0 |
| isyatirimhisse_vs_borsapy | ocf              | 100 |       0       |              0 |
| isyatirimhisse_vs_borsapy | revenue          | 100 |       0       |              0 |
| isyatirimhisse_vs_borsapy | total_assets     | 128 |       0       |              0 |
