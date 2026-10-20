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
