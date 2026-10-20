# Cap Rate Lens

A data tool for exploring how cap rate movements reshape ASX-listed property
trust valuations: NTA sensitivity, leverage amplification, Monte Carlo
outcome ranges, covenant headroom, and sector exposure, all built on
manually-verified public ASX announcement data for eight major trusts.

**Live app:** https://web-theta-puce-54.vercel.app
**API:** https://cap-rate-lens-api-production.up.railway.app

Built as a public portfolio project, drawing on real property-fund valuation
work, but using only public data. No confidential or proprietary data is
used anywhere in this repo.

## What it does

- **Fund detail** — NTA, WACR, gearing, WALE for each fund; move a cap rate
  slider and watch NTA per security respond in real time, via the standard
  income-capitalisation valuation identity with leverage amplification.
- **Market comparison** — all eight funds side by side, sortable, each row
  linking to its primary source document; a leverage risk ranking (NTA
  impact of a uniform +100bp cap rate shock) and a covenant headroom
  ranking (clearly labelled as a modelling assumption, since no fund
  discloses an actual covenant).
- **Sector exposure** — donut charts per fund, built from whatever exposure
  split each fund actually reports (some report an official percentage
  table, others only dollar or income figures that had to be converted).
- **Cap rate risk premium** — a fund's WACR plotted against the live
  10-year Australian government bond yield over time, the spread between
  them shaded to show whether property is pricing in more or less risk than
  the risk-free rate.
- **Monte Carlo NTA range** — 5,000 draws of a random cap rate shift applied
  to the valuation model, reported as p10/p25/p50/p75/p90, instead of a
  single point estimate.
- **Portfolio builder** — combine holdings across funds to see blended
  gearing, WACR, sector exposure, and a combined sensitivity curve.
- **Deterministic commentary** — a few sentences per fund generated from
  fixed templates filled with the figures already on the page, never
  free-form text, so nothing stated can be a number the data doesn't back.

Every data point that isn't model output is a link to the primary ASX
announcement it came from. Anything not yet confirmed shows `n/a` rather
than a guess.

## Architecture

```
┌─────────────────┐        ┌──────────────────────┐        ┌─────────────────────┐
│  React + Vite    │  REST  │  FastAPI (Python)     │        │  RBA statistics      │
│  + TypeScript     │◄──────►│  valuation + sector   │◄──────►│  (live bond yield)   │
│  + Tailwind v4    │        │  models over static    │        └─────────────────────┘
│  (Vercel)          │        │  JSON fund data        │
└──────────────────┘        │  (Railway)              │
                              └──────────────────────┘
                                        ▲
                                        │  manually sourced, cited inline
                                        │
                              ASX company announcements
                              (read directly, not via search summaries)
```

- **Frontend** (`web/`): React + TypeScript + Vite + Tailwind CSS v4. All
  charts are hand-built SVG components (`web/src/Charts.tsx`), no charting
  library. Theming is CSS custom properties with a light/dark split driven
  by `prefers-color-scheme`.
- **Backend** (`api/`): FastAPI. `valuation.py` holds the pure math (NTA
  sensitivity, leverage-adjusted sensitivity, Monte Carlo, covenant
  headroom, the two-factor cap-rate × NOI-growth heatmap). `main.py` wires
  those into endpoints over the static dataset in `api/data/`.
- **Data**: `api/data/funds.json` and `api/data/sector_exposure.json` are
  hand-curated from each fund's own ASX announcements, every figure carries
  a `source` and `source_url`. The one live, fully-automated data source is
  `api/rba_bond_yields.py`, which fetches the RBA's daily 10-year government
  bond yield (table F2, series FCMYGBAG10D) directly, with a 12-hour cache
  and stale-cache fallback.

## Why the data isn't fully automated

ASX's own announcements platform prohibits automated scraping under its
Terms of Use, and each fund's investor-relations site would need separate,
individually-confirmed automation (several sit behind JS-rendered widgets
or bot protection). That investigation, what was tried, what's blocked, and
what a real fix would look like, is written up in
[`docs/phase1-pipeline-status.md`](docs/phase1-pipeline-status.md) rather
than quietly skipped. Today, new figures are added by fetching the specific
primary-source PDF and reading it directly, the same process used to build
the current dataset, not by trusting a search engine's AI summary.

## Running locally

**Backend**

```bash
cd api
python -m venv .venv
.venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend**

```bash
cd web
npm install
npm run dev
```

The dev server proxies to `http://localhost:8000` by default (see
`web/src/api.ts`); set `VITE_API_BASE` to point elsewhere.

**Tests**

```bash
cd api
pip install -r requirements-dev.txt
pytest
```

Unit tests cover the pure valuation math (`tests/test_valuation.py`) and the
RBA CSV parsing / volatility calibration (`tests/test_rba_bond_yields.py`),
against hand-worked expected values rather than just checking the code runs.

## Honest limitations

- Coverage is eight funds, not the full ASX property sector.
- Several fields (sector splits, WALE breakdowns, a stated covenant
  gearing threshold) are either calculated from indirect figures or not
  disclosed by the fund at all, each case is labelled rather than guessed.
- The Monte Carlo standard deviation is a simplifying assumption, not fitted
  to historical cap rate volatility, there isn't yet enough public quarterly
  history to estimate that properly.
- Data freshness depends on a manual re-read of each fund's next results
  release; there is no scheduled refresh job.

## Author

Built by Ishaan Pala, a junior analyst working in property fund valuation.
This project demonstrates the same cap rate / NTA / leverage mechanics used
day to day in that role, reimplemented from scratch on public data.
