# Phase 1 (automated data pipeline) — status as of 2026-10-20

Written so this isn't lost or re-investigated from scratch later.

## Done

- **1c — RBA bond yield feed: fully automated and live.** `api/rba_bond_yields.py`
  fetches the RBA's daily 10-year AGS yield (table F2, series FCMYGBAG10D)
  directly, caches it for 12h, and falls back to the last good cache if the
  fetch fails. No manual step involved. This is the one piece of this tool's
  data that is genuinely live.

## Explicitly ruled out

- **Scraping `announcements.asx.com.au` directly.** ASX's own Terms of Use
  prohibit automated scraping ("any spider, screen scraper, robot... unless
  ASX gives prior written consent") and restrict commercial use. Checked
  2026-10-19. Do not build against this domain without written ASX consent.

## Investigated, not worth pursuing further right now

**Goal:** automatically discover and download each fund's quarterly/annual
results PDFs from their own investor-relations (IR) site, instead of me
manually searching/fetching them each session.

**robots.txt check (2026-10-19), for reference if revisited:**
| Fund | robots.txt | Notes |
|---|---|---|
| Dexus | permissive | see below, discovery still failed |
| Mirvac | permissive | announcements URL not yet confirmed |
| Stockland | permissive | announcements URL not yet confirmed |
| Goodman | permissive (`Disallow:` empty) | announcements URL not yet confirmed |
| Vicinity | permissive (`Disallow:` empty) | announcements URL not yet confirmed |
| GPT Group | permissive (standard Drupal boilerplate) | announcements URL not yet confirmed |
| Charter Hall | **blocked** — Cloudflare bot-challenge blocks even a plain robots.txt fetch | Not automatable without defeating bot-detection. Will not attempt. |
| Scentre Group | N/A | Next.js SPA; plain HTTP fetch returns an empty app shell with no PDF links in the HTML |

**What was actually tried for Dexus** (`scripts/fetch_announcements.py`,
kept as a starting point, not currently wired into anything automated):
1. Plain HTTP fetch (httpx) of
   `dexus.com/investor-centre/listed-funds/dexus-dxs/results-and-reporting/asx-announcements`
   — returned 29 PDF links, but all distribution notices / tax statements /
   historical documents, not the actual results announcements.
2. Playwright (headless Chromium, full JS render, `networkidle` wait) of the
   same URL — returned 39 PDF links (media releases + the same distribution
   docs), still no FY/half-year results PDF among them.

**Conclusion:** the actual results-announcement feed on this page is not
in the rendered DOM at this URL. It's likely served by a separate
third-party investor-hub widget/platform (common for ASX-listed companies)
that isn't linked directly from this page — finding it would mean more
per-fund investigation (inspecting network requests, trying other URLs on
the same site), with no guarantee of success, and the same unknown-cost
problem would repeat for each of the other 5 unconfirmed funds.

**Decision (2026-10-20):** not worth the uncertain time/effort cost for a
solo portfolio project right now. Paused, not abandoned — Playwright is
already installed in the project venv if this gets picked up again.

## What ships instead for now

Semi-automated extraction, same as used for all 8 funds' current data: when
new figures are needed, fetch the specific PDF (found via search or a known
URL) and read it directly rather than trusting a search summary, same
process used throughout this session. No scheduled job, no unattended run.

## If this gets picked up again

1. For each unconfirmed fund (Mirvac, Stockland, Goodman, Vicinity, GPT),
   open their investor-relations page in a real browser and use dev tools
   (Network tab) to find the actual API/endpoint the announcements widget
   calls — that's almost certainly a cleaner integration point than scraping
   rendered HTML.
2. Only add a `FundSource` to `scripts/fetch_announcements.py` once that
   endpoint is confirmed and legal (check that specific endpoint/site's
   terms, not just the main domain's robots.txt).
3. Charter Hall and Scentre need a different approach entirely (manual, or
   revisit if their site architecture changes) — don't retry the same method.

## Follow-up: second WACR snapshot per fund (not yet done, 2026-10-20)

The cap rate risk premium chart (`/funds/{id}/spread`, Fund detail tab) only
renders for a fund when at least two of its snapshots each have a WACR, since
it plots WACR vs. bond yield over time, not a single point. Today that's true
for exactly one fund:

- **DXS**: FY26 (6.06%) and 1H26 (6.19%) WACR both sourced — chart renders.
- **GPT**: has two snapshots (1H26, FY25) but FY25's WACR was never sourced
  (`null`) — correctly excluded rather than gap-filled, but means no chart.
- All other 6 funds (CLW, MGR, SGP, GMG, SCG, VCX) only have one snapshot
  tracked at all.

**Next step, when picked up:** source a second historical WACR per fund (the
prior half-year/full-year result) the same way the current single-snapshot
data was sourced — read the primary ASX PDF directly, don't trust search
summaries.

## Update 2026-10-20: GPT fixed, found a real data bug along the way

Went to fill in GPT's missing FY25 WACR (the lowest-effort target above) and
found something worse than a gap: the existing `wacr_pct: 6.26` on GPT's
1H26 snapshot was wrong. A web search summary had reported it as the
fund's headline WACR; reading both primary ASX PDFs directly (GPT's 2026
Interim Result, 17 Aug 2026, and 2025 Annual Result, 16 Feb 2026) showed
GPT doesn't publish one portfolio-wide WACR at all, only a separate figure
per segment (Retail, Office, Logistics). 6.26% was specifically the
**Office segment's** cap rate, mislabeled as the fund-wide figure.

Fixed in `api/data/funds.json`: GPT's `wacr_pct` is now `null` on both
snapshots (honest, since no single figure exists to report), with `sectors`
populated per segment (Office, Logistics — Retail's cap rate is disclosed
but has no WALE in either release, so it's left out of the `sectors` array
rather than guessing a WALE to make it fit the schema; noted in `source`).
Gearing was also backfilled for FY25 (31.1%, was previously `null`).

Net effect: GPT now has accurate data but dropped out of the leverage
ranking and risk-premium chart, both of which need a single `wacr_pct`.
That's the correct trade, a feature working on wrong data is worse than it
not working. If a portfolio-level figure is ever needed for GPT, it would
have to be a value-weighted combination of the per-sector cap rates against
`sector_exposure.json`'s income-share weights, clearly labelled as
calculated rather than reported, same pattern already used for its NTA
sector-exposure split.

This is a good reminder that "GPT's missing WACR" and "every fund's
single-snapshot WACR already in the dataset" should both be re-verified
against primary sources before being trusted, not just the gaps — a wrong
number is worse than a missing one.
