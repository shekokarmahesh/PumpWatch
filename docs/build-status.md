# Build status

## Implemented and verified locally

The full replay path works: five fictional scenarios, all four screens, eight signals, candidate confirmation, evidence/rule disclosure, registry demo matching, local watchlists, idempotent daily snapshots, real observation history, exports and request logs. Past searches lists the latest saved report per stock, including stocks off the watchlist. A restart integration test verifies SQLite persistence and opening a saved report without collection. Backend integration tests block accidental network connections. Frontend tests exercise evidence disclosure, missing values, local saved-report matching and API errors. OpenAPI-generated types compile against the production build.

Live collection was tested on 8 October 2026 for Reliance, TCS, Orient Cables and Moneyview. Compact YouTube dates, provider instrument-name suffixes and overly short request timeouts caused missing evidence; fixes have regression coverage. Provider empty results and timeouts now have separate explanations. Short IPO price histories do not establish a historical volume baseline. See [live-testing.md](live-testing.md) for observed scores and remaining gaps.

The UI refresh uses adapted beUI motion primitives, a dark theme, bento cards, animated report scores, and interactive hype/support charts. Component provenance and open licenses are documented in [ui-sources.md](ui-sources.md). Browser checks covered search confirmation, saving a stock, evidence expansion and scoring rules, daily snapshot idempotency, chart toggles, and 1280px/390px layouts. The mobile chart tooltip overflow was fixed. Fonts are self-hosted for offline replay. The frontend test suite and production build pass.

## Required before a credible live submission

1. Expand the four-stock smoke test into five reviewed real-stock fixtures. Choose any enforcement examples only after verifying the cited order; do not infer wrongdoing from the PRD.
2. Confirm each engine's real response for Indian SME listings, including quarterly financials, graph timestamps/volume, YouTube date filters and Google News nesting.
3. Inspect Ads Transparency name/domain search behaviour. This MVP makes one company query; a second promoter query is not yet implemented. Attribution is deliberately conservative when a creative has no identifying text.
4. Download and review complete SEBI RA/IA lists, including validity. The current command imports reviewed CSVs; automatic downloads still need implementation after confirming the published format.
5. Import reviewed NSE Emerge/BSE SME lists with source and capture dates. The shipped real lists are empty.
6. Broaden latency and account-credit verification. The smoke tests completed in 0.4–13.3 seconds with a mixture of fresh and cached responses; this does not establish the 30-second target across all uncached stocks or provider conditions.
7. Decide whether to enable the opt-in GitHub snapshot schedule. Persisted baselines are needed for useful cheap snapshots; a new ticker can initially be insufficient.
8. Create the GitHub repository, record the demo and complete the submission. No external publication, account setup, registration or submission was performed.

## Explicit PRD interpretations

- Company-name lookup uses Google Search discovery followed by Finance verification, because sending plain names directly to the Finance engine failed for the tested recent listings. This adds one discovery request to the PRD's proposed one-call resolution flow. Bare symbols are tried directly before discovery, and normalized queries reuse the local cache.
- Missing support yields Insufficient data. It is not coerced into zero to assign High risk.
- The support score is labelled **Fundamentals & support**, since news coverage and promoter names are not financial fundamentals.
- Four-quarter revenue trend uses latest revenue minus earliest revenue; net-income sign uses the four-quarter aggregate. All inputs are exposed.
- Registry name matching is not identity verification. Demo rows are separate, and unverified/stale real registries yield Not checked.
- Local 24-hour cache reuse also applies to live mode, to satisfy the PRD's requirement not to repeat identical paid requests in a day.
- No fabricated daily trend is seeded. Historical curves build from persisted observations.
- Replay examples are synthetic, explicitly labelled, and reproducible. They do not yet satisfy the PRD's live-captured fixture criterion.
