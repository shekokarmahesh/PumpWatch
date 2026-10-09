# PumpWatch

Look beyond the stock tip. PumpWatch compares public attention with supporting evidence for Indian stocks, using six SerpApi search engines and transparent scoring rules.

**This tool measures public attention, not value. It is not investment advice.** A low attention-risk score does not establish safety, value or legitimacy.

## Run the demo

Requires Python **3.12+** and Node **20.19+** with npm or pnpm. From this directory:

```sh
git clone https://github.com/shekokarmahesh/PumpWatch.git
cd PumpWatch
python3 scripts/run.py
```

Open **http://127.0.0.1:8000**. The first run installs dependencies and builds the frontend; subsequent starts can use `python3 scripts/run.py --skip-install`. On Windows use `py -3.12 scripts/run.py`. API documentation is at `/docs`.

The default mode is **replay**, and it makes **zero network calls at runtime**. Dependency installation requires internet access. Five bundled **fictional** companies cover High, Elevated, Low and Insufficient data outcomes. All observations, promoter registry rows and evidence links in these scenarios are simulated, not captured market evidence. The interface and exported reports say so explicitly. No historical curve is invented: it starts with the first observation.

| Fictional scenario | Hype | Support | Verdict |
| --- | ---: | ---: | --- |
| Pulse Components · PULSE:NSE | 100 | 0 | High |
| Aster Industries · ASTER:NSE | 43.12 | 22.5 | Elevated |
| Northstar Systems · NORTHSTAR:NSE | 0.74 | 100 | Low |
| Orbit Consumer · ORBIT:BOM | 0 | 90 | Low |
| Sparrow Materials · SPARROW:BOM | 13.33 | Unknown | Insufficient data |

## What works

- Company-name, partial-name and ticker search with explicit candidate confirmation. You can enter names such as `Jindal Supreme` or `Adroit Industries`; exchange-qualified symbols remain optional. Matching saved reports appear while typing and open directly with a click or Arrow keys + Enter, without a provider lookup.
- Eight explainable signals, weighted hype/support scores and evidence-linked reasons.
- Evidence cards, scoring inputs, promoter match details and a collapsible call/credit log.
- SQLite persistence, a searchable Past searches section, saved reports, watchlist management with undo removal, and daily snapshots with carried-data labels. Reopening a report uses no SerpApi requests.
- Hype history with new promoter/ad markers and an accessible observation table.
- Markdown and JSON exports, including evidence, timestamps and the disclaimer.
- Live/cache-first/replay collection through the same collectors, official SerpApi Python SDK, disk caching, bounded concurrency and rate-limit retries.
- Generated OpenAPI TypeScript types, replay integration tests and CI checks.

The [UI/UX review](docs/ux-review.md) records the search, mobile readability and report-flow improvements and their verification.

## Live data

Copy `.env.example` to `.env` and set `PUMPWATCH_MODE=cache-first` and `SERPAPI_KEY` **locally**. Restart with the launcher. Never put the key in frontend code or commit `.env`.

Live collection was exercised with the configured account on **8 October 2026** for Reliance, TCS, Orient Cables and Moneyview. Results and limitations are recorded in [docs/live-testing.md](docs/live-testing.md). There are no real registry or SME-list records bundled yet. Real promoter checks remain **Not checked** until verified CSVs are imported; unknown SME status is never inferred from a ticker. The remaining validation work is listed in [docs/build-status.md](docs/build-status.md).

The full path uses eight distinct collector requests. A company-name lookup uses one Google Search request to discover Indian listings and one Finance request to verify the leading match. A symbol with an exchange uses Finance directly. Bare symbols are tried on NSE (numeric codes on BSE); an unmatched single-word name can therefore use one extra Finance attempt before name discovery. Verified name matches are stored in SQLite, so choosing the leading match needs no additional discovery call; choosing another candidate can require one Finance verification. Daily snapshots reuse Finance 1M, YouTube this month and Trends. Local 24-hour caching applies in both live and cache-first modes; replay refuses fixture misses. A shared semaphore permits four requests at a time. The local budget reserves in-flight requests and conservatively counts unknown transport failures. This is a local estimate, not the account's authoritative balance; spending outside this app is not visible. Consult the SerpApi dashboard for billed usage.

SerpApi is the only runtime external data service. Engines and source documentation: [Finance](https://serpapi.com/google-finance-api), [YouTube](https://serpapi.com/youtube-search-api), [Trends](https://serpapi.com/google-trends-api), [Search](https://serpapi.com/search-api), [News](https://serpapi.com/google-news-api), [Ads Transparency](https://serpapi.com/google-ads-transparency-center-api). The backend uses the [official Python SDK](https://github.com/serpapi/serpapi-python).

The local monthly and rolling-hour budgets each default to 250 requests. Set `PUMPWATCH_MONTHLY_BUDGET` and `PUMPWATCH_HOURLY_BUDGET` in `.env` to match your account, then restart the backend. The sidebar shows both local estimates; these can exceed billed usage because unknown transport failures remain reserved. SerpApi's free [Account API](https://serpapi.com/account-api) reports the authoritative balance and hourly allowance. On 10 October 2026, the configured account reported an hourly allowance of 250; the previous local limit of 50 blocked searches prematurely. Clearing search history preserves the credit ledger and raw response cache.

## Develop and verify

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
PYTHONPATH=backend .venv/bin/python -m app.cli openapi
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend generate-api
pnpm --dir frontend test
pnpm --dir frontend build
```

For frontend development, run `PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:create_app --factory --reload` and `pnpm --dir frontend dev` in separate terminals. Vite proxies `/api` to port 8000. On Windows PowerShell, set `$env:PYTHONPATH='backend'` and use `.venv\Scripts\python.exe`.

CLI commands:

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli analyse PULSE:NSE
PYTHONPATH=backend .venv/bin/python -m app.cli snapshot
PYTHONPATH=backend .venv/bin/python -m app.cli capture-fixtures RELIANCE:NSE TCS:NSE --output .local/live-fixtures
```

Capture requires a local key. It preserves raw responses, parameters and actual timestamps into a **separate folder**. Review the captured data before replacing the synthetic fixture directory. Never describe the generated scenarios as live captures. `scripts/generate_demo_fixtures.py` rebuilds the synthetic examples.

## Registry and exchange data

The verified registry CSVs are deliberately empty. Download the current Research Analyst and Investment Adviser lists from SEBI, review completeness and normalize them into `name,registration_number,registry_type,valid_until` CSVs. Then import:

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli refresh-registry \
  --research-analysts /path/to/ra.csv --investment-advisers /path/to/ia.csv \
  --captured-at YYYY-MM-DD --source-url https://www.sebi.gov.in/your-verified-source \
  --verified-complete
```

This import command intentionally does not claim to scrape SEBI. The current downloadable format and refresh automation still need verification. Registry matching uses exact names, normalized names, then similarity > 0.9. Fuzzy matches are always **Possible match**, never confirmed registration. A **Not found** name is not proof of unregistered activity. Recorded validity is checked; imported data expires after 30 days. Demo registry rows are isolated from real runs.

Reviewed SME records go into `backend/data/exchanges/sme.csv` with `symbol,exchange,company_name,listing_date`; a missing row leaves listing status unverified. Record download dates and sources alongside imported lists before using them in the hackathon.

## Scoring

All scoring happens in Python. Available signals are combined as `sum(weight × score) / sum(available weights)`. Empty responses are unknown; nonempty samples with no qualifying items can produce an observed zero. Evidence is required for any scored signal. Each evidence card shows the exact rule and inputs.

Hype weights are video velocity **30%**, search spike **25%**, tip-group density **20%**, paid promotion **15%**, price-volume anomaly **10%**. Support weights are news coverage **40%**, four-quarter financial trend **35%**, registered promoter names **25%**.

The PRD verdict thresholds are implemented. As an explicit conservative extension, absent support gives **Insufficient data**, because treating unknown support as zero would create an unsupported High verdict. Financial trend is defined as revenue change from the earliest to latest of four complete reported quarters and the sign of their aggregate net income. These choices are visible in the rules and inputs.

YouTube counts cover returned search samples, not all uploads. Relative month dates use 30-day approximations, including compact provider dates such as `6d ago`. Price volume is aggregated by day before comparing graph windows; a volume baseline must include observations older than the last 30 days. A newly listed stock may therefore have insufficient history. Ads are counted only when returned text or advertiser names can be attributed to the stock; company advertising alone does not establish a stock recommendation. News coverage measures visibility rather than endorsement.

## Daily snapshots

Use the watchlist's **Take daily snapshot** action or the CLI. Repeated snapshots on an IST calendar day are skipped. The three-request job reuses prior video/volume baselines and unavailable signal values with explicit **carried** labels. A fresh ticker without a full-analysis baseline may have insufficient data. History contains one latest observation per day and retains source run IDs.

`.github/workflows/snapshot.yml` defines the 09:30 IST schedule but scheduled execution is **opt-in**: set repository variable `ENABLE_DAILY_SNAPSHOTS=true`. It defaults to replay and an empty `snapshots/watchlist.json`. Populate that list with explicit ticker keys. To use live data, configure repository variable `PUMPWATCH_MODE=cache-first` and secret `SERPAPI_KEY`. The job restores local state from GitHub cache and commits only exported observation JSON. Cache eviction can lose baselines and local credit accounting; review the account budget before enabling live runs. Publishing this workflow does not opt the repository into scheduled runs.

## Architecture and storage

```text
React / CLI / snapshot job
          ↓
FastAPI → resolver → concurrent collectors → registry → scorer → SQLite
                            ↓
                    shared cache gateway
                     ↙              ↘
            replay fixtures     SerpApi SDK
```

`backend/app/core/collectors/` has one module per engine. Raw JSON stays on disk; six SQLite tables hold tickers, calls, signals, evidence, promoter matches and scores. Local state is under `.local/` and is ignored by version control. The production Vite build is served directly by FastAPI; no Docker or Redis is required.

## AI disclosure

This initial implementation was created with Codex from the supplied PRD, including source code, synthetic scenario generation and tests. Scoring is deterministic; no LLM participates in analysis. Financial/legal claims in the PRD were not adopted as product facts without verification. This repository is a working development MVP, not a finished hackathon submission.
