# UI/UX review — 9 October 2026

Implemented using the local ui-ux-pro-max skill, preserving the existing dark green visual design and animated signal orbit.

| Priority | Friction found | Implemented improvement |
| --- | --- | --- |
| High | Returning to a company required searching or scrolling through saved reports. | Local saved-report suggestions, keyboard selection, exact saved-name/symbol submission, and recent-report shortcuts open the stored report directly. Typing does not call a provider. |
| High | “Analyse” described a company lookup and left the next step unclear. | Separate Search, Finding, company confirmation and Analysing states. A new company requires an explicit Analyse choice. |
| High | Failed queries offered little recovery and old results could outlive an edited query. | Preserve input, focus the field on lookup failure, show an inline error with retry, and cancel/ignore outdated requests when the query changes. Empty responses have a recovery message. |
| High | Small text and touch controls made phone use difficult. | 16px search/filter inputs, larger narrative and evidence text, clearer secondary contrast, 44px minimum key controls, and a visible three-item mobile navigation. |
| Medium | Saved reports created a long page and narrow score columns clipped data. | Recent five by default, view all, labelled filter, clear-filter and new-search empty-state actions; full-width company details and two score columns on phones. |
| Medium | The report history competed with the explanation for attention. | Put key reasons before a collapsed history panel; history mounts when opened. Downloads sit behind a disclosure, and missing aggregate scores say Unknown. |
| Medium | Watchlist actions were ambiguous and removals were easy to regret. | Explicit Add/Remove labels, pending and saved feedback, and an Undo removal action on the watchlist. |
| Medium | Provider exchange identifiers leaked into report and saved-list labels. | Friendly NSE/BSE labels with the symbol; internal route keys remain compatible. |

## Verification

- Frontend: 14 tests pass, including eight search behavior tests for keyboard/pointer selection, direct saved submission, explicit company confirmation, retry, request cancellation, empty results and clearing the field.
- Backend regression suite: 53 tests pass. One existing Starlette/httpx deprecation warning remains.
- Production TypeScript/Vite build passes.
- Browser review at 1280×900, 390×844 and 320×760. Reviewed search, saved reports, overview, evidence and watchlist. No page-wide horizontal overflow in the reviewed layouts; narrow saved-score clipping was found and fixed.
- Browser-confirmed saved-report keyboard and pointer opening, demo search → company confirmation → saved report, failed-query recovery controls, saved-list filtering/clearing/view all, report history/download disclosures, and watchlist add/remove/undo.
- Measured search input at 16px; desktop navigation at 44px high, mobile navigation at 58px and primary Search at 48px. Browser console contained no warnings or errors during the review.
- Runtime review used replay mode and a separate SQLite backup under `.local/ux-preview`, with an empty API key. No SerpApi requests were made and the original saved reports/watchlist were not changed by preview interactions. Live provider relevance was not retested in this UI pass.

Screenshots are local review artifacts, ignored by version control:

- [Desktop saved-report search](../.local/ux-review/search-desktop.png)
- [Mobile saved-report search](../.local/ux-review/search-mobile.png)
- [320px saved-report cards](../.local/ux-review/saved-reports-320.png)

The temporary preview was stopped after verification, respecting the earlier request to leave the frontend and backend stopped.
