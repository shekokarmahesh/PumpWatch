# Live test record — 8 October 2026

Four NSE stocks were analysed through the running FastAPI backend using the configured SerpApi account and the existing 24-hour response cache. These are observed search samples, not investment recommendations.

| Stock | Symbol | Hype /100 | Hype signals available | Verdict |
| --- | --- | ---: | ---: | --- |
| Reliance Industries | RELIANCE:NSE | 30.41 | 4/5 | Low |
| Tata Consultancy Services | TCS:NSE | 46.15 | 3/5 | Low |
| Orient Cables | ORIENTCABL:NSE | 76.00 | 2/5 | Insufficient data |
| Moneyview | MONEYVIEW:NSE | 73.33 | 3/5 | Low |

All four had recognised news coverage. The displayed support score was 100 based on **news alone**, with only 1/3 support signals available. It does not mean that financial health or promoter registration was verified. The overview now prominently displays partial coverage.

## Reproduced and corrected

- YouTube returned dates such as `6d ago`; the parser previously discarded them. A minimal captured response reproduces the failure and verifies usable dated evidence after the fix.
- Finance resolved Moneyview as “Moneyview Ord Shs”. The instrument suffix was passed to the search engines. It is now removed from company queries.
- Company attribution now recognises “Orient Cables” when the resolved label is “Orient Cables (India) Ltd”, while rejecting unrelated “Orient Electric” titles.
- Requests were capped at six seconds. They now allow up to twelve seconds within the analysis deadline. The rerun recovered Orient Cables search, news and longer finance responses. TCS's indexed tip-group request still timed out and remains unknown.
- A new listing's one-month and one-year graph can contain the same few trading days. A price-volume score now requires volume observations older than the last 30 days. Orient had three recent days and Moneyview four; neither has a comparable historical volume baseline.
- Provider “no results” messages are distinguished from request failures. Neither is converted into an observed zero. Other provider errors are not reused as valid cached responses.

## Company-name lookup

Plain names previously went directly to Google Finance, which returned no results for Jindal Supreme and Adroit Industries. Name lookup now uses Google Search's finance answer box or official Finance/NSE/BSE quote links, filters for the entered company, and verifies the leading listing through Finance. Bare symbols and numeric BSE codes also work without an exchange suffix. Partial or ambiguous names offer matching listings for confirmation; unrelated and foreign quotes are excluded.

The running backend returned these results on 8 October 2026:

| Entered query | Resolved listing | Company |
| --- | --- | --- |
| Jindal Supreme | JSIPL:NSE | Jindal Supreme India |
| Adroit Industries | 544950:BOM (BSE) | Adroit Industries (India) Limited |
| jindal sup | 544935:BOM (BSE) | Jindal Supreme India |
| ADROITIND | ADROITIND:NSE | Adroit Industries (India) Limited |

The full-name and bare-symbol checks reused cached provider responses. The successful partial-name check included a fresh request. These are lookup tests, not new full analyses. The browser confirmed that entering each full company name displays the correct confirmation card. Search fixtures cover partial matches, duplicate listings, foreign results, mismatched company names and explicit symbols. Case and extra spaces are normalized. Name discovery allows a twenty-second provider timeout within a thirty-second lookup deadline; collector requests retain their twelve-second cap. Initial partial-name and bare-symbol discovery attempts timed out before these changes, and timeouts remain possible if the provider is unavailable.

Verified leading matches are persisted as ticker records; a name-only lookup does not create a scored report in Past searches. Choosing a verified match avoids an additional discovery request. Normalized name queries and quote verification reuse the existing twenty-four-hour response cache. A saved report still opens directly from SQLite.

Local lookup results are recorded in `.local/company-name-test-results.json`.

## Persisted reports

The existing SQLite score records were already saved. `/api/searches` now exposes the most recent report per stock, its timestamp, coverage and saved-run count. The home page lists and filters these as **Past searches**. Searching a saved company offers **Open saved report** and **Analyse again** separately.

Opening a saved report reads SQLite and makes no SerpApi requests. Backend integration checks verified deduplication, latest-run ordering, limits and persistence across a new application instance. Browser checks verified a repeated Moneyview search, opening its saved report and page reload.

## Remaining source gaps

The finance responses did not include four complete quarterly income statements. A verified current SEBI registry has not been imported. Ads Transparency returned no results for these queries. Orient Cables had no non-zero historical Trends baseline, so only two hype signals could be scored; it retains **Insufficient data** despite available videos and news.

Run summaries are kept locally in `.local/live-test-results.json`; raw provider responses and SQLite state remain under `.local/`. Credentials are not included in these summaries. Local credit accounting is conservative and is not the provider's billed account balance.

## Demo lookup and budget verification — 10 October 2026

The configured SerpApi account reported 110 billed searches out of 250, 140 remaining, and an hourly allowance of 250. PumpWatch's separate rolling-hour limit was still 50 and had reached that limit, despite its monthly estimate being 121/250. The local hourly setting and default now use 250. Both local windows appear in the sidebar as estimates, and blocked requests identify which window is exhausted without reserving a credit. The monthly cap remains 250; clearing report history does not reset the ledger.

The running backend successfully resolved `Runwal Enterprises`, `Reliance Industries`, and `ESDS Software` to `RUNWALENTR:NSE`, `RELIANCE:NSE`, and `ESDS:NSE`. Google Search returned a finance answer titled "News" alongside the correct company name in its knowledge graph for Reliance and ESDS. Filtering company matches before deduplicating listings fixes that failure; both cases have regression tests. The frontend company picker was verified for Runwal and ESDS. These checks created no saved score reports. Three fresh search responses were fetched; cached Finance verification responses were reused.

Validation: 59 backend tests and 14 frontend tests passed, Python lint passed, and the production frontend build passed. A registry test now calculates its fixture dates in IST, matching the registry implementation and preventing a UTC/IST date-boundary failure.
