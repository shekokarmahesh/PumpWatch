# Stock Hype Detector PRD

Oct 8, 2026 · @Mobile Team 1

## Summary

PumpWatch (working name) tells a retail investor whether an Indian small-cap or SME stock is being hyped faster than its fundamentals justify. The user enters an NSE or BSE ticker. The tool pulls six Google surfaces through SerpApi, matches the people promoting the stock against SEBI's registry of licensed analysts, and returns a hype score, a fundamentals score, a verdict, and every piece of evidence as a link. A watchlist re-checks tickers daily so the hype curve builds over time.

This is an entry for the SerpApi India Hackathon 2026 in the Commerce & Market Intelligence track. Submission deadline is Oct 10, 2026 at 23:59 IST. It is a solo build over three days: a Python backend and a TypeScript front end. The product is an awareness and research tool, not investment advice, and says so on every screen.

## Problem and market context

Pump-and-dump schemes in Indian SME and small-cap stocks run in public, on Google surfaces, and nobody gives retail investors a tool that reads those surfaces together. The promotion happens on YouTube, Telegram, WhatsApp and paid Google ads weeks before the dump. The signals are visible one at a time but never combined, so an investor who searches the stock sees enthusiasm, not a pattern.

- In May 2026 SEBI barred seven people and impounded ₹20.25 crore from a family-run pump-and-dump across 82 SME stocks, run through X, Telegram and over 50 WhatsApp groups. None of the promoters was a registered research analyst. [Moneylife](https://moneylife.in/article/father-sons-wives-and-daughters-sebi-busts-alleged-familyrun-2025-crore-fininfluencer-pumpanddump-scam-in-sme/80551.html)
- SEBI requires anyone giving stock recommendations to hold a research analyst or investment adviser registration. As of 30 September 2024 there were 1,358 registered research analysts and 953 registered investment advisers, a small set that is easy to check against. [SEBI](https://www.sebi.gov.in/media/press-releases/jun-2016/sebi-cautions-public-to-deal-only-with-sebi-registered-investment-advisers-and-research-analysts_32627.html)
- SEBI's own advice is to verify registration on its website before acting on a tip. Almost nobody does, because the check is manual and the promoter's name is buried in a video or a group.

The gap is not data. The data is public. The gap is that no product measures hype against fundamentals for a named stock and shows the evidence. That is what this project builds.

## Goals and non-goals

The goal is a working tool that a judge can run locally in under five minutes and that produces a defensible verdict for any NSE or BSE ticker, with every number traceable to a SerpApi response.

**Goals**

- Give one ticker a hype score, a fundamentals score and a verdict in under 30 seconds on live data.
- Show the evidence behind every signal as a clickable link to the video, page, ad or news item.
- Flag promoters who are not in SEBI's research analyst or investment adviser registry.
- Keep a watchlist and take a daily snapshot so the hype curve is visible over time.
- Run end to end with zero API calls in replay mode, from fixtures shipped in the repo.
- Stay inside the SerpApi free plan of 250 searches per month for the whole build and demo.

**Non-goals**

- No buy, sell or hold recommendation. The tool describes attention, not value.
- No real-time or intraday data. Daily granularity is enough to see a pump build.
- No coverage of mutual funds, derivatives, crypto or non-Indian listings.
- No user accounts, payments or hosted service. It runs locally.
- No scraping of Telegram or WhatsApp content directly. Only what Google indexes, through SerpApi.
- No machine-learned model. Scoring is rule-based and explainable so judges can audit it.

## Target users and personas

The primary user is a retail investor who has just received a tip and wants a second opinion in one minute. Two secondary users shape the evidence design: a financial journalist and a compliance analyst.

| Persona | Situation | What they need from the tool | What they do with it |
| --- | --- | --- | --- |
| Retail investor, 25 to 45, Tier 1 or Tier 2 city | A WhatsApp group or YouTube channel named a stock with a target price | A plain verdict and the top three reasons, in one screen | Decides whether to ignore the tip or dig further |
| Financial journalist | Investigating a stock that moved 60 percent in a month on no news | Dated evidence links, promoter names, ad history, exportable | Cites the evidence in a story or files a query with SEBI |
| Compliance or surveillance analyst at a broker or exchange | Screening SME listings for unusual attention | A watchlist with daily snapshots and the unregistered-promoter flag | Escalates a ticker for review |
| Hackathon judge | Evaluating in under ten minutes | A one-command run, a replay mode, and visible SerpApi dependence | Scores the five criteria |

## User stories

Each story is in scope for the hackathon build and has a testable acceptance line.

| ID | Story | Acceptance criteria |
| --- | --- | --- |
| US-1 | As an investor, I enter a ticker or company name and get a verdict with a hype score and a fundamentals score. | Entering RELIANCE:NSE or a partial name resolves to one ticker. Verdict, both scores and the top three reasons render in under 30 s live, under 2 s in replay. |
| US-2 | As an investor, I can click any reason and see the exact evidence behind it. | Every reason links to the YouTube video, Google result, news article or ad creative it came from. No reason exists without a link. |
| US-3 | As an investor, I see which promoters are not SEBI-registered. | Channel and advertiser names are matched against the registry. Each is marked Registered, Not found, or Possible match with the matched registry row shown. |
| US-4 | As an analyst, I add tickers to a watchlist and see a daily hype curve. | A ticker on the watchlist gets one snapshot per day. The curve shows hype score per day with a marker for each new signal. |
| US-5 | As a judge, I run the full app without a SerpApi key. | Setting the mode to replay serves five bundled tickers from fixtures. All tests pass in replay in CI. |
| US-6 | As a judge, I can see exactly which SerpApi calls were made for a result. | A debug panel lists each engine, its parameters, cache hit or miss, and the credit spent. |
| US-7 | As a journalist, I can export the evidence for a ticker. | One click downloads a JSON and a Markdown report with all signals, links and timestamps. |

## Functional requirements

Seven capabilities make up the product. FR-1 to FR-4 are the core analysis path and must ship. FR-5 to FR-7 make the result trustworthy and are what separate this entry from a one-shot script.

**FR-1 Ticker resolution**

- Accept a symbol with exchange (RELIANCE:NSE, 543XXX:BOM) or a company name.
- Resolve a name through one Google Finance call and offer the top match for confirmation.
- Flag whether the ticker is on NSE Emerge or BSE SME from the bundled exchange lists.

**FR-2 Signal collection**

- Call the six SerpApi engines listed under Data sources, each in its own collector module with a fixed parameter set.
- Store every raw response on disk keyed by a hash of engine plus parameters before any parsing.
- Normalize each response into a typed signal record: value, unit, time window, list of evidence items with URL, title, source, date.
- Treat an empty or missing result as no data, never as zero. The scorer must distinguish the two.

**FR-3 Scoring**

- Compute a hype score and a fundamentals score, each 0 to 100, from the signal records using the rules in the scoring section.
- Produce a verdict of Low, Elevated or High attention risk.
- Produce the top three reasons, each tied to one signal and its evidence list.

**FR-4 Evidence panel**

- Show each signal as a card with its value, its window, and its evidence items as links.
- Show the raw SerpApi parameters and the cache status for each call in a collapsible debug view.

**FR-5 Registry matching**

- Load SEBI's research analyst and investment adviser lists from a bundled CSV with a documented refresh script.
- Match YouTube channel names and ad advertiser names with exact, then normalized, then fuzzy matching above a 0.9 similarity threshold.
- Label each promoter Registered, Possible match, or Not found, and show the matched row.

**FR-6 Watchlist and snapshots**

- Let the user add and remove tickers from a local watchlist.
- Run a daily snapshot job that collects the three cheapest signals per ticker and stores a score row.
- Plot hype score per day per ticker with markers on days a new promoter or ad appeared.

**FR-7 Replay mode**

- Honour an environment variable with values live, cache-first and replay.
- In replay, serve every call from bundled fixtures for five tickers and refuse to make network calls.
- Ship fixtures captured from live runs during the build, with capture dates recorded.

## Signals and scoring model

The model compares an attention side (five hype signals) against a legitimacy side (three support signals). Every signal is a rule on one SerpApi response, scored 0 to 100, so a judge can recompute any number by hand from the evidence panel.

| Signal | Side | Engine | Measure | Score rule (0 to 100) | Weight |
| --- | --- | --- | --- | --- | --- |
| Video velocity | Hype | YouTube | V30 = videos in last 30 days with a buy-call keyword in title; B = same count for days 31 to 90, divided by 2 | 100 × log2((V30 + 1) / (B + 1)) / 3, clamped. An 8× jump scores 100 | 0.30 |
| Search spike | Hype | Google Trends, geo IN | R = mean of last 4 weekly values / median of prior 48 weeks | 100 × (R − 1) / 4, clamped. A 5× rise scores 100 | 0.25 |
| Tip-group density | Hype | Google Search, past month | N = organic results on t.me, whatsapp.com or chat.whatsapp.com whose title or snippet has target, multibagger or buy call | min(100, 20 × N) | 0.20 |
| Paid promotion | Hype | Ads Transparency Center, region 2356 | A = ad creatives shown in last 90 days that name the stock or a promoter | min(100, 35 × A) | 0.15 |
| Price-volume anomaly | Hype | Google Finance | One-month return and 30-day average volume against the one-year average | 100 if return above 40 % and volume above 3× baseline; 50 if one holds; else 0 | 0.10 |
| News coverage | Support | Google News, India | S = distinct recognised outlets with an item in last 30 days | min(100, 25 × S) | 0.40 |
| Financial trend | Support | Google Finance financials | Last four quarters: revenue growth sign and net income sign | 100 if both positive; 50 if one; 0 if neither | 0.35 |
| Registered promoters | Support | YouTube + Ads + SEBI registry | P = share of distinct promoters marked Registered, when at least 2 promoters were found | 100 × P | 0.25 |

Buy-call keywords are a fixed list in the repo: target, multibagger, buy, breakout, rocket, 100 percent, and their Hindi transliterations. A signal whose response is empty is marked no data and drops out of the weighted mean, so a thinly covered stock is not punished for silence.

Each side is the weighted mean of its available signals:

```latex
\text{Hype} = \frac{\sum_{i \in \text{available}} w_i \, s_i}{\sum_{i \in \text{available}} w_i}
```

The same formula gives Support from the three legitimacy signals. The verdict follows four rules, checked in order:

1. Insufficient data when fewer than three hype signals have data. No verdict is shown, only the signals that exist.
2. High when Hype is at least 60 and Support is at most 40.
3. Elevated when Hype is at least 40 and Hype minus Support is at least 20, or when any single hype signal scores 100 while Support is under 50.
4. Low otherwise.

The top three reasons are the three highest-scoring hype signals, each with its evidence list. An SME listing is shown as a context badge and does not change scores in this version.

## Data sources

SerpApi is the only network dependency. All six engines are reached through one endpoint and one API key, and each call costs one search credit. The registries are static files bundled in the repo.

| Engine value | Purpose | Fixed parameters | Fields read | Credits per full analysis |
| --- | --- | --- | --- | --- |
| google\_finance | Price, volume, financials, name resolution | q = SYMBOL:NSE or CODE:BOM; window = 1M, then 1Y | summary.price, graph\[\].price and volume, financials\[\], knowledge\_graph.key\_stats | 2 |
| youtube | Video hype and promoter channel names | search\_query = company name + target; sp = this month, then this year | video\_results\[\].title, views, published\_date, channel.name, link | 2 |
| google\_trends | India search interest | q = company name; geo = IN; data\_type = TIMESERIES; date = today 12-m | interest\_over\_time.timeline\_data\[\].values | 1 |
| google | Tip-group pages | q = company name + target OR multibagger, site:t.me OR site:chat.whatsapp.com; gl = in; hl = en; tbs = qdr:m | organic\_results\[\].title, snippet, link, date | 1 |
| google\_news | Genuine coverage | q = company name; gl = in; hl = en | news\_results\[\].title, source.name, date, link | 1 |
| google\_ads\_transparency\_center | Paid promotion in India | text = company name, then each promoter name; region = 2356 | ad\_creatives\[\].advertiser, format, first\_shown, last\_shown, total\_days\_shown, link | 1 to 2 |

A full analysis costs 8 to 9 credits. A daily watchlist snapshot uses only google\_finance with window 1M, youtube this month, and google\_trends, for 3 credits per ticker. Identical calls within one hour are served from SerpApi's cache at no cost, and failed calls are not charged. [SerpApi pricing](https://serpapi.com/pricing)

| Static source | Purpose | Format | Refresh |
| --- | --- | --- | --- |
| SEBI registered research analysts | Promoter registration check | CSV, name, registration number, validity | Script in repo re-downloads from sebi.gov.in; captured date recorded in the file header |
| SEBI registered investment advisers | Same | CSV | Same script |
| NSE Emerge and BSE SME lists | SME context badge | CSV, symbol, company name, listing date | Downloaded manually, since both sites block scripts |
| Recognised news outlets | Distinct-source count for news coverage | Text list of about 40 domains | Edited by hand |

All SerpApi parameter names and field names above are from the engine documentation: [Google Finance](https://serpapi.com/google-finance-api), [YouTube](https://serpapi.com/youtube-search-api), [Google Trends](https://serpapi.com/google-trends-api), [Google Search](https://serpapi.com/search-api), [Google News](https://serpapi.com/google-news-api), [Ads Transparency Center](https://serpapi.com/google-ads-transparency-center-api).

## System architecture

&#91;embedded content: system architecture · 3 entry points, 6 collectors, 1 external service\]

The React UI talks only to FastAPI, while the CLI and the cron call the orchestrator directly. Every collector goes through the cache layer, which is the only place SerpApi is called and the only place fixtures are read, so live and replay share one code path. Results land in SQLite and the entry points read them back.

## Data flow

One analysis is a straight pipeline of collect, normalize, match, score, render. The daily snapshot reuses the first three steps on a smaller signal set.

**One analysis, triggered from the React UI through the API, or from the CLI**

1. The React UI posts a ticker or name to the analyse endpoint. The resolver calls google\_finance once, confirms the symbol and exchange, and checks the bundled SME list.
2. The orchestrator asks each of the six collectors for its signal. Collectors run concurrently with a cap of four in flight, to stay under SerpApi's 50 searches per hour on the free plan.
3. Each collector builds its parameter set, hashes it, and asks the cache layer. In replay mode the cache layer only reads fixtures. In cache-first mode a hit within 24 hours is returned. In live mode a miss goes to SerpApi and the raw JSON is written to disk before anything else happens.
4. Each collector normalizes its raw JSON into a signal record with a value, a window and a list of evidence items.
5. The registry matcher takes every promoter name from the YouTube and Ads records and labels it against the SEBI CSVs.
6. The scorer computes the eight signal scores, the two side scores, the verdict and the top three reasons.
7. The result is stored as a score row and returned as JSON, which the React UI renders on the verdict and evidence routes. The debug panel reads the call log written in step 3.

**Daily snapshot, triggered by the scheduler**

1. The scheduler reads the watchlist and, for each ticker, runs only the google\_finance 1M, youtube this-month and google\_trends collectors.
2. Steps 3 to 6 above run unchanged. Signals without fresh data reuse the previous day's value and are marked carried.
3. A score row is appended with the date. The hype curve reads these rows.
4. In the hackathon build the scheduler is a GitHub Actions cron that commits the new rows to the repo, so the history is visible to judges without a server.

## Data model

Six tables in one SQLite file hold everything the app produces. Raw SerpApi responses stay on disk as JSON files and are referenced by path, never copied into the database.

| Table | Purpose | Key fields |
| --- | --- | --- |
| tickers | One row per analysed or watched stock | symbol, exchange, company\_name, is\_sme, on\_watchlist, first\_seen\_at |
| calls | Log of every SerpApi request | id, engine, params\_hash, params\_json, mode (live, cache, replay), cache\_hit, credits\_spent, raw\_path, fetched\_at, status |
| signals | One normalized signal per ticker per run | id, ticker\_id, run\_id, name, side (hype, support), value, unit, window\_start, window\_end, has\_data, score, call\_id |
| evidence | Items behind a signal | id, signal\_id, url, title, source, published\_at, promoter\_name, promoter\_status |
| promoters | Registry match results, reused across runs | name\_normalized, status (registered, possible, not\_found), registry\_type (RA, IA), registry\_row\_json, similarity, matched\_at |
| scores | One row per run, the watchlist curve reads these | id, ticker\_id, run\_at, hype\_score, support\_score, verdict, reasons\_json, signals\_available, snapshot (true for scheduled runs) |

A run is identified by ticker plus timestamp. Fixtures for replay mode are the raw JSON files plus a manifest that maps params\_hash to file path, so replay and live share the same cache code path.

## Backend API

FastAPI exposes nine endpoints under /api and documents them automatically at /docs, so a judge can exercise the backend without the front end. Response models are pydantic, and the front end's TypeScript types are generated from the OpenAPI schema so the two sides cannot drift.

| Method and path | Purpose | Request | Response |
| --- | --- | --- | --- |
| GET /api/health | Liveness and current mode | none | mode, credits spent this month, bundled fixture tickers |
| POST /api/resolve | Turn a name or symbol into candidates | query | up to 5 candidates with symbol, exchange, company name, is\_sme |
| POST /api/analyse | Run one full analysis, synchronous | symbol, exchange | run\_id, verdict, hype\_score, support\_score, reasons, signals with evidence and promoter labels |
| GET /api/runs/{run\_id} | Fetch a past result | none | same payload as analyse |
| GET /api/runs/{run\_id}/calls | Debug table | none | one row per SerpApi call: engine, params, mode, cache\_hit, credits, fetched\_at |
| GET /api/runs/{run\_id}/export | Journalist export | format = json or md | file download |
| GET /api/tickers/{symbol}/history | Hype curve | days, default 30 | score rows by date with new-promoter and new-ad markers |
| GET, POST, DELETE /api/watchlist | Manage the watchlist | symbol on POST and DELETE | current watchlist with latest verdict per ticker |
| POST /api/snapshot | Trigger a snapshot from the UI | optional symbol | rows written. The GitHub Action uses the CLI instead, since no server runs there |

The analyse call is synchronous and returns inside the 30-second live budget; the UI shows one loading state. CORS allows the Vite dev origin on port 5173. For a judge's run, the built front end is served by FastAPI from a static directory, so one command starts everything.

## UI and screens

The app has four screens and a persistent disclaimer bar. The verdict screen is the one the demo video and the judges will spend their time on, so it carries the evidence design.

| Screen | Route | Purpose | Elements | Primary action |
| --- | --- | --- | --- | --- |
| Search | / | Entry point | Ticker or name input, mode indicator (live, cache-first, replay), five bundled example tickers as buttons | Analyse |
| Verdict | /t/$symbol | The answer | Verdict badge (Low, Elevated, High, Insufficient data); hype and support scores as two horizontal meters; top three reasons, each with a one-line why and an evidence count; SME badge; last-run time | Expand a reason, add to watchlist, export |
| Evidence | /t/$symbol/evidence | The proof | One card per signal: value, window, score, and its evidence items as links with source and date; promoter chips coloured by registry status; collapsible debug table of SerpApi calls with engine, parameters, cache status and credits | Open a link, copy parameters |
| Watchlist | /watchlist | The trend | Table of watched tickers with latest verdict and scores; hype-curve line chart per ticker with markers on days a new promoter or ad appeared | Remove ticker, open verdict |

Design rules for the build:

- Every number on screen is clickable and leads to the signal card that produced it.
- Colour carries one meaning only: registry status on promoter chips and verdict level on the badge. Nothing else is coloured.
- The disclaimer bar reads: This tool measures public attention, not value. It is not investment advice. It stays visible on every screen.
- The debug table is collapsed by default and expanded in the demo video, because it is the fastest way to show judges the SerpApi dependence.
- The front end is React with TypeScript, built with Vite, routed with TanStack Router's file-based routes, and fetching through TanStack Query. The hype curve is one Recharts line chart.
- All scoring stays in the backend. The front end never computes a score, only renders what the API returns.

## Non-functional requirements

The binding constraint is the SerpApi free plan: 250 searches per month and 50 per hour. Every other requirement follows from running a credible demo inside that budget in three days.

| Area | Requirement |
| --- | --- |
| Credit budget | A full analysis uses at most 9 credits. A daily snapshot uses at most 3 per ticker. The whole build, snapshots and demo stay under 250. The call log makes spend visible at all times. |
| Caching | Every raw response is written to disk before parsing. Cache-first mode serves any hit under 24 hours old. Identical parameters never hit SerpApi twice in a day. |
| Replay | Replay mode serves five bundled tickers with zero network calls. CI runs the full test suite in replay. The README's first run instruction uses replay so a judge sees results before entering a key. |
| Performance | Live analysis completes in under 30 seconds with four collectors in flight. Replay completes in under 2 seconds. Every other API endpoint answers in under 200 ms from SQLite. |
| Rate limiting | Concurrency is capped at four. On a 429 the collector waits with exponential backoff and jitter, up to three tries, then marks the signal no data. |
| Reliability | A failed collector never fails the run. The scorer works on whatever signals have data and reports which are missing. |
| Reproducibility | Scoring is deterministic. The same fixtures always produce the same scores, and the test suite asserts the expected scores for the five bundled tickers. |
| Explainability | Every score links to its rule, its inputs and its evidence. No hidden weights, no model weights. |
| Portability | Python 3.12 backend and Node 20 front end, SQLite, no Docker required. Redis is optional and only through docker-compose. Runs on macOS, Linux and Windows. |
| Disclaimer | The not-investment-advice notice is on every screen, in the README, and in the exported report. |

Planned credit spend for 8 to 10 October:

| Activity | Credits |
| --- | --- |
| Build and test, moving to fixtures after first capture of five tickers | 80 |
| Daily snapshots, five tickers at 3 credits, three days | 45 |
| Demo recording on live data, two tickers | 20 |
| Reserve for retries and re-captures | 50 |
| Total | 195 of 250 |

## Tech stack and repository layout

Python on the backend, because the judges are Python and Ruby developer advocates and the five community awards go through Python user groups. TypeScript and React on the front end, which is what the judges see first. Every dependency is free. The backend installs with one command and the front end with one more.

| Layer | Choice | Reason |
| --- | --- | --- |
| Backend language | Python 3.12 | Judges' home language; fastest path in three days |
| API | FastAPI with uvicorn | Automatic OpenAPI docs at /docs; pydantic models shared with the core package |
| SerpApi client | Official serpapi Python package | Judges maintain it; shows SDK use on the submission form |
| Core package | Plain Python modules, pydantic models | Typed signal records, no framework lock-in |
| Concurrency | asyncio with a semaphore of 4 | Stays under the hourly rate limit |
| Storage | SQLite through SQLModel, raw JSON on disk | Zero setup, inspectable by judges |
| Cache | Disk JSON keyed by parameter hash | Doubles as the fixture format for replay; no extra service |
| Redis | Not in the hackathon build | Disk cache and SQLite already cover caching, and a Docker dependency slows a judge's first run. A docker-compose file with Redis is kept for a job queue if snapshots ever move off GitHub Actions |
| Fuzzy matching | rapidfuzz | Fast token-set ratio for promoter names against the SEBI CSV |
| Front end | React with TypeScript, Vite, TanStack Router, TanStack Query, Recharts | File-based routes, cached fetches, one chart for the hype curve |
| API types | openapi-typescript generated from the FastAPI schema | Front end and backend share one contract; a drift fails the build |
| CLI | Typer | analyse, snapshot, capture-fixtures, refresh-registry commands |
| Scheduler | GitHub Actions cron, daily at 09:30 IST | Free, visible history in the repo, no server |
| Tests | pytest in replay mode; Vitest for the front end | Deterministic, no credits spent in CI |
| Optional LLM | Off by default behind a flag | Keyword rules are enough and reproducible |

Repository layout:

```
pumpwatch/
  backend/
    app/
      main.py              # FastAPI app, CORS, static serving of the built front end
      api/                 # routers: health, resolve, analyse, runs, watchlist, snapshot
      core/
        resolver.py        # ticker and name resolution
        collectors/        # one module per SerpApi engine
          finance.py  youtube.py  trends.py  search.py  news.py  ads.py
        cache.py           # live, cache-first, replay; raw JSON on disk
        normalize.py       # raw JSON to signal records
        registry.py        # SEBI CSV loading and fuzzy matching
        scorer.py          # signal rules, side scores, verdict, reasons
        models.py          # pydantic and SQLModel types
        store.py           # SQLite access
      cli.py               # Typer commands
    data/
      registry/            # SEBI RA and IA CSVs with capture dates
      exchanges/           # NSE Emerge and BSE SME lists
      fixtures/            # raw SerpApi JSON for five tickers plus manifest
      outlets.txt          # recognised news domains
    tests/
    pyproject.toml
  frontend/
    src/
      routes/              # TanStack Router file routes
        __root.tsx  index.tsx  t.$symbol.tsx  t.$symbol.evidence.tsx  watchlist.tsx
      api/                 # generated OpenAPI types and a typed fetch client
      components/          # VerdictCard, SignalCard, PromoterChip, HypeCurve, DebugTable
    package.json  vite.config.ts  tsconfig.json
  snapshots/               # daily score rows committed by the Action
  .github/workflows/       # ci.yml (pytest in replay, vitest), snapshot.yml (daily cron)
  docker-compose.yml       # optional, Redis only
  README.md
```

## Build plan

&#91;embedded content: build plan · 3 days, 3 gates\]

Each day ends at a gate. If a gate slips, the next day's scope is cut from the bottom of its list, never from the gate. Fixtures are captured on day one so that days two and three spend almost no credits.

## Risks and mitigations

The two risks that can sink the entry are running out of credits before the demo and a thin SME ticker returning empty signals. Both are handled by design, not by hope.

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Credits exhausted before the demo video | Medium | High | Capture fixtures for five tickers on day one and develop against them. Call log shows spend. 50-credit reserve. |
| Google Finance does not know a small SME ticker | Medium | Medium | Try SYMBOL:NSE, then CODE:BOM, then a name search. If all fail, mark price signals no data and continue. |
| YouTube results are noisy or in Hindi | High | Medium | Require the company name plus a buy-call keyword in the title. Keyword list includes Hindi transliterations. Dedupe by video id. |
| Google Trends returns empty for a low-volume name | High | Low | No data, not zero. The signal drops out of the weighted mean. |
| Ads Transparency has no creatives for most stocks | High | Low | Weight is 0.15 and the signal is no data when empty. When it fires, it is the strongest reason and is shown first. |
| SEBI name matching misses a registered promoter | Medium | Medium | Three-stage match with a 0.9 fuzzy threshold. Possible match is a distinct label and shows the candidate row. Never label Not found below 2 promoters. |
| Rate limit of 50 per hour hit during capture | Low | Medium | Semaphore of 4, backoff on 429, capture script spreads tickers across hours. |
| Judge cannot run it | Low | High | Replay mode is the first README instruction. CI badge proves tests pass in replay. Demo video shows the same commands. |
| Perceived as investment advice | Low | High | Disclaimer on every screen and in exports. No buy, sell or hold language anywhere in the UI or README. |
| Scope creep in three days | High | High | FR-1 to FR-4 ship by end of day two. FR-5 to FR-7 only after. Nothing outside the functional requirements list. |

## Judging criteria mapping and success metrics

The hackathon scores five criteria. Each one maps to a specific, demonstrable part of the build, and the demo video walks them in this order.

| Criterion | What the judges ask | Where this project answers it |
| --- | --- | --- |
| Idea strength | Is there a clear and compelling insight? | Hype is measurable on public Google surfaces before the dump, and nobody combines those surfaces for a named stock. The May 2026 SEBI case is the opening of the README. |
| Originality | Something distinctive or thoughtfully recombined? | Six engines fused into one verdict. Ads Transparency Center and Google Finance appear in almost no SerpApi projects on GitHub. Zero visible competitors in finance surveillance among hackathon repos as of 7 October. |
| Technical complexity | Meaningful engineering effort? | Concurrent collectors with a shared cache and replay layer, deterministic multi-signal scoring, three-stage registry matching, scheduled snapshots with committed history, full test suite, and a typed React front end generated from the FastAPI OpenAPI schema. |
| Usefulness | Would the intended user get practical value? | A one-minute second opinion on a tip, with evidence links a journalist or analyst can act on. |
| Meaningful SerpApi usage | Does the project depend on search data? | Every signal is a SerpApi response. The debug table shows each call. Remove SerpApi and nothing works. |

Success metrics for the submission itself:

- Five bundled tickers produce verdicts in replay with no key, and the test suite passes in CI.
- At least one live ticker in the demo shows a High or Elevated verdict with an unregistered promoter and a linked ad or video.
- The README's first command runs in under five minutes on a clean machine.
- Total SerpApi spend for the hackathon stays under 250 credits.
- Submission is in by 18:00 IST on 10 October, six hours before the deadline.

## Submission checklist

Everything the submission dashboard asks for, in the order it asks.

- [ ] Project name, one-paragraph description, track set to Commerce & Market Intelligence
- [ ] Public GitHub repository with README: problem, SEBI case, quick start in replay, quick start live, architecture, scoring rules, SerpApi usage, AI tools disclosure, disclaimer
- [ ] SerpApi usage statement naming the six engines and the official Python SDK, and stating that SerpApi is the sole data source
- [ ] Demo video under three minutes: replay run, live run on one ticker, evidence panel, debug table of SerpApi calls, watchlist curve
- [ ] Video link opens without sign-in (unlisted YouTube or public Drive link tested in a private window)
- [ ] Lead participant name, email, mobile, occupation, years of experience
- [ ] Pre-existing project status set to new
- [ ] AI tools used listed, with how they were used
- [ ] Rules and terms accepted
- [ ] Community affiliation noted if a partner Python user group was joined
- [ ] Submitted by 18:00 IST on 10 October, then edited only for typos

## Open questions

- [ ] Which five tickers become the bundled fixtures? Two should be stocks named in the May 2026 SEBI order, two large caps as controls, one recent SME listing.
- [ ] Does Google Finance through SerpApi return quarterly financials for SME-board stocks, or only for main-board ones? Verify on day one with two SME tickers.
- [ ] Which SEBI list format is current for download, and does it include validity dates? Confirm before writing the refresh script.
- [ ] Is the YouTube engine's upload-date filter reliable for the this-month window, or should the window be computed client-side from published\_date?
- [ ] Should the watchlist snapshot run in GitHub Actions against the real key, or stay local for the hackathon to protect credits?
- [ ] Which partner community, if any, to join before submission for the Best from Community award?

* [ ] Is per-collector progress worth a streaming endpoint, or is one loading state on the analyse call enough for the demo?
