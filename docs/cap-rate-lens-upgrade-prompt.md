# Cap Rate Lens — v2 upgrade brief

You built Cap Rate Lens with me and have full context on the codebase. This brief takes it from a demo to a genuinely advanced tool that a property analyst or fund manager would actually use, and that stands out as a portfolio piece for data and tech roles.

**Before you write any code:** read this whole brief, look over the current codebase, then reply with a phased plan. For each item, include effort estimates, dependencies, and anything you think is infeasible or a bad idea. Push back where I'm wrong. Work in the phase order below and commit after each phase. Don't start the next phase until the current one builds, its tests pass, and you've checked the UI in a browser.

**Non-negotiable rules that carry over from v1:**
- Never invent or estimate a figure to fill a gap. Missing data stays visibly missing, with a reason.
- Every number must trace back to a source: document, page, and extraction date.
- Every modelling assumption is stated in the UI next to the output it affects.

---

## Phase 0 — Fix what's already broken or inconsistent

1. The page `<title>` is "web". Set a real title, a favicon, and an Open Graph and Twitter card image. Generate the OG image dynamically with the headline stat (e.g. `@vercel/og`).
2. The About page claims the comparison table is sortable by any metric. Make every column header sortable, with direction indicators and keyboard access.
3. The About page mentions a fan chart, but Monte Carlo output is only shown as percentile text. Build the actual chart (Phase 3 covers the design).
4. The Market comparison tab looks disabled when it isn't selected. Fix the contrast on inactive tabs.
5. "+1% cap rate" is ambiguous. Use basis points everywhere ("+100bp").
6. DXS shows WALE as n/a, while sector WALEs (4.1y, 4.4y) appear right below. Either compute a value-weighted WALE and label it as derived, or explain why not.
7. Table "n/a" currently mixes two meanings. Split it into "Not reported by fund" and "Pending extraction", and give each a tooltip.
8. Flag stale snapshots. CLW is as of Dec 2025 while the others are June 2026. Show an age badge and dim any row older than the latest reporting period.
9. The risk premium chart has two data points, which is too few to say "compressed". Soften the copy until there is more history (Phase 1 backfills it).

---

## Phase 1 — Automated data pipeline (the most important phase)

Goal: the dataset refreshes itself every reporting season, and every value can be audited.

### 1a. Ingestion
- For each tracked ticker, poll the ASX company announcements feed for new results-related documents: half-year and full-year results, property portfolio and valuation updates, quarterly updates. Research what endpoints are available and their terms of use before building on any of them. If the feed isn't usable, fall back to each fund's investor-relations page and tell me which approach you chose and why.
- Store the raw PDFs with a content hash, using object storage or the repo with Git LFS (your call; justify it). Never re-download unchanged files.
- Run the job on a schedule with GitHub Actions cron or Vercel cron: daily during reporting season (Feb and Aug), weekly otherwise.

### 1b. Extraction
- Turn each PDF into text plus tables with layout preserved (pdfplumber, camelot, or similar). Keep page numbers.
- Use an LLM extraction step that returns structured output against a strict schema (zod or pydantic): WACR, sector cap rates, gearing, NTA per security, WALE, occupancy, total portfolio value, sector values, cost of debt, % debt hedged, weighted debt maturity, ICR, look-through gearing vs balance-sheet gearing, FFO and distribution per security. **Every extracted field must include the source page and the verbatim snippet it came from.** Null is a valid answer. Prompt the extractor so that null is preferred over guessing.
- Validate in code, not by trusting the LLM:
  - Range checks: WACR must be between 3% and 10%.
  - Accounting identities: does NTA × securities roughly equal net assets? Does the sector sum roughly equal the portfolio total?
  - Period-on-period jumps above a threshold get flagged.
  - The snippet must actually contain the number.
- Failed or low-confidence values go to a **review queue**, not to production. Build a simple admin page (password or Vercel-protected) where I approve, edit, or reject each value with the PDF page shown beside it. Approved values are written to a versioned dataset (JSON or SQLite in the repo, or Postgres, your call) with full provenance.

### 1c. Market and macro data (fully automatic)
- 10-year AGS yield from the RBA statistical tables (F2) CSV, fetched daily. Replace the FRED quarterly series and the Trading Economics one-off point. Backfill as far as the RBA series goes.
- Daily closing security prices for all tracked funds. Check licensing and reliability for the source you pick, cache the results, and show the "as of" timestamp. If no acceptable free source exists, tell me rather than scraping something fragile.
- Optional: the RBA cash rate and BBSW, for cost-of-debt context.

### 1d. Backfill
- Run the pipeline over the last 5–8 years of results for all eight funds, so every chart has real history.

### 1e. Data transparency in the UI
- Hovering or clicking any number opens a provenance popover: source document, page, snippet, extraction date, and who approved it.
- Add a public **Data status page** with coverage per fund and field, last refresh, pipeline run history, and open review items. This shows engineering maturity better than any chart.

---

## Phase 2 — Analyses others won't think of (the differentiators)

Each analysis must state its formula and assumptions in the UI and in the About page, with unit tests against hand-calculated cases.

1. **Market-implied cap rate.** This is the headline feature. Book NTA uses valuers' cap rates, while the share price reflects what the market believes. Reverse the valuation model: find the cap rate at which modelled NTA equals the current security price, holding debt fixed. Show book WACR vs implied cap rate, and the spread in basis points, for every fund over time. In plain language: "The market is pricing DXS as if its cap rate were 7.1%, which is 104bp wider than valuers say." Also show premium or discount to NTA alongside.
2. **Valuation lag and desmoothing.** Appraisal-based values lag reality. Apply a Geltner-style desmoothing to the book value series to estimate an unsmoothed one, and compare it to the listed-price signal. Explain clearly, and caveat the method.
3. **Covenant breaking point.** Using reported covenant thresholds where disclosed (otherwise a clearly labelled assumption, such as a 50% gearing covenant), solve for the cap rate at which gearing breaches the covenant, plus the distance to it in bp. Do the same for ICR using cost of debt and hedging: the interest-rate rise at which ICR hits its covenant. Rank funds by headroom.
4. **Two-factor sensitivity heatmap.** Show cap rate shift against NOI growth, with the NTA % change in each cell, the current point marked, and a contour line where NTA is unchanged ("how much rent growth you need to offset X bp of cap rate expansion").
5. **Refinancing shock.** Combine the debt maturity profile, hedge percentage and current swap rates to project cost of debt and FFO per security over 1–3 years as hedges roll off.
6. **Historical regime scenarios.** Preset buttons that apply real historical cap-rate moves (the GFC-era expansion, the 2022–24 rate cycle) to today's balance sheets. Sourcing must be documented, with no made-up magnitudes. If you can't source a regime properly, leave it out.
7. **Calibrated Monte Carlo.** Once the backfill exists, replace the assumed ±50bp normal distribution with one fitted to historical WACR changes. Offer fat tails (Student-t), and draw cap-rate shocks jointly with bond yield moves using their historical correlation. Keep a toggle back to the simple assumption, and show which one is active.
8. **Does the spread predict anything?** Run a simple backtest: when the cap-rate–bond spread or the implied-vs-book gap was unusually wide or narrow, what happened to book cap rates over the next 6–12 months? Report it honestly, including if the answer is "weakly" or "no". A null result presented well is still impressive.
9. **Portfolio builder.** Let users enter holdings (ticker and amount) and see aggregate look-through sector exposure, weighted gearing, a combined NTA sensitivity curve, and a combined Monte Carlo result.
10. **Automated plain-English commentary.** For each fund, generate a short templated narrative from the numbers, such as "Gearing is in the top quartile of the group, and the market-implied cap rate is 90bp wider than book, the widest gap in 3 years." Use deterministic templates, not free-form LLM text, so it can never hallucinate.

---

## Phase 3 — Visual design: make it look authored, not generated

The installed taste skill isn't moving the output far enough from default AI aesthetics. Treat the following as hard constraints that override defaults.

**Pick a direction.** Mock up three distinct directions as static pages first, screenshot them, and let me choose:
- (a) **Annual report / FT editorial:** warm paper background, serif display type, ruled hairlines, footnoted numbers, salmon or deep green accent.
- (b) **Terminal:** dense, monospaced, high information density, amber or green on near-black, keyboard-first.
- (c) **Swiss data design:** strict grid, one strong accent, huge numerals, generous whitespace.

**Banned, because they read as AI slop:**
- Gradient glows or blobs, glassmorphism, uniform rounded-2xl card grids
- Pill badges on everything, emoji, sparkle icons, generic Inter on #0a0a0a
- Purple-blue gradients, centred hero with a vague tagline, identical padding everywhere
- Shadcn defaults left unstyled, "Built with ❤️" footers

**Required:**
- Real typographic hierarchy (a display face, a text face, and tabular figures).
- Charts annotated directly in the plot, editorial style: label the line ends, call out the notable point ("Widest gap since 2023"). No legend boxes if direct labels work.
- A consistent number format system: bp vs %, $ with 2 decimal places, negatives in a defined colour.
- Dense where analysts need density (tables), spacious where readers need a story.

**Flashy but useful** (every animation must explain something, not just decorate):
- **NTA bridge waterfall:** asset value → minus debt → NTA, animating as the slider moves, so the leverage amplification is visible rather than just described.
- **Scrollytelling landing section:** one fund walked through in 4–5 scroll steps (cap rate → asset value → debt → NTA → market price → implied cap rate), ending at the live tool.
- **Monte Carlo fan chart** that streams in the simulated draws, then settles into percentile bands.
- **Animated number transitions** on slider moves, using tabular figures so nothing jitters.
- **⌘K command palette:** jump to a fund, run a scenario, change a metric. Plus keyboard shortcuts (1–8 to switch funds, ←/→ for the slider).
- **Shareable state:** every scenario (fund, cap rate, preset, portfolio) is encoded in the URL, and the OG image renders that scenario.
- **Export:** download the current fund's model as an `.xlsx` with **live Excel formulas** (not pasted values) and source citations, plus a one-page PDF tear sheet per fund. This is very valuable for the target audience.

---

## Phase 4 — Engineering quality (what reviewers check)

- Unit tests for every formula, including golden tests that match a hand-built Excel model to the cent.
- Schema validation on every data load. The app must fail loudly on malformed data.
- An end-to-end smoke test with Playwright: load each tab, move the slider, sort the table.
- Lighthouse score of 90+ on performance and accessibility. WCAG AA contrast, charts usable by keyboard with text alternatives, `prefers-reduced-motion` respected.
- A README with an architecture diagram (pipeline → validation → review → dataset → app), setup steps, and a "decisions and trade-offs" section.
- A **Case study** page in the app: problem, approach, the hardest technical problem (likely PDF extraction accuracy), extraction accuracy metrics from the review queue, and what I'd do next. Written for a hiring manager.

---

## Phase 5 — Stretch (only if everything above is solid)

- Expand coverage beyond 8 funds to the full S&P/ASX 200 A-REIT index.
- Alerts: email when a fund publishes new results, or when the implied-vs-book gap crosses a threshold.
- A property-level map for funds that disclose asset lists.
- A "Compare two funds" split view.

---

## How to report back

At the end of each phase, give me:
- What shipped
- Screenshots
- Anything you skipped and why
- Data coverage numbers
- Any assumption you had to make that I should check

If something in this brief conflicts with good practice or with the data's honesty rules, the honesty rules win. Flag the conflict.
