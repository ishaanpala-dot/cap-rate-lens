import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import rba_bond_yields
from valuation import leverage_adjusted_sensitivity, monte_carlo_nta, nta_sensitivity

app = FastAPI(title="cap-rate-lens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent / "data"
FUNDS = json.loads((DATA_DIR / "funds.json").read_text())["funds"]
FUNDS_BY_ID = {f["id"]: f for f in FUNDS}
SECTOR_EXPOSURE = json.loads((DATA_DIR / "sector_exposure.json").read_text())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/funds")
def list_funds():
    return [{"id": f["id"], "name": f["name"], "ticker": f["ticker"]} for f in FUNDS]


def _computed_wale(fund: dict, snapshot: dict) -> dict | None:
    """Value-weight the snapshot's per-sector WALEs by that fund's sector_exposure
    percentages, when both exist and the headline WALE wasn't reported. Only
    covers the sectors we have a percentage for, so coverage is usually partial
    and must be stated, not silently treated as the whole portfolio."""
    if snapshot.get("wale_years") is not None or not snapshot.get("sectors"):
        return None
    exposure = next((e for e in SECTOR_EXPOSURE["funds"] if e["id"] == fund["id"]), None)
    if not exposure:
        return None
    exposure_by_sector = {s["sector"]: s["pct"] for s in exposure["sectors"]}

    covered_pct = 0.0
    weighted_sum = 0.0
    for s in snapshot["sectors"]:
        pct = exposure_by_sector.get(s["sector"])
        if pct is None:
            continue
        covered_pct += pct
        weighted_sum += pct * s["wale_years"]

    if covered_pct == 0:
        return None

    return {
        "value": round(weighted_sum / covered_pct, 1),
        "coverage_pct": round(covered_pct, 1),
    }


@app.get("/compare")
def compare_funds():
    """Latest snapshot across every tracked fund, for the market-wide comparison view."""
    rows = []
    for f in FUNDS:
        snap = f["snapshots"][0]
        rows.append(
            {
                "id": f["id"],
                "name": f["name"],
                "ticker": f["ticker"],
                "period": snap["period"],
                "as_of": snap["as_of"],
                "nta_per_security": snap["nta_per_security"],
                "wacr_pct": snap["wacr_pct"],
                "gearing_pct": snap["gearing_pct"],
                "wale_years": snap.get("wale_years"),
                "occupancy_pct": snap.get("occupancy_pct"),
                "computed_wale": _computed_wale(f, snap),
            }
        )
    return rows


@app.get("/funds/{fund_id}")
def get_fund(fund_id: str):
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    fund = dict(fund)
    fund["snapshots"] = [dict(s) for s in fund["snapshots"]]
    for snap in fund["snapshots"]:
        snap["computed_wale"] = _computed_wale(fund, snap)
    return fund


@app.get("/funds/{fund_id}/sensitivity")
def get_sensitivity(fund_id: str, new_cap_rate_pct: float, snapshot_index: int = 0):
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    snapshot = fund["snapshots"][snapshot_index]
    if snapshot["wacr_pct"] is None or snapshot["gearing_pct"] is None:
        raise HTTPException(
            status_code=422,
            detail="This snapshot is missing WACR or gearing data, so sensitivity can't be computed",
        )

    result = nta_sensitivity(
        nta_per_security=snapshot["nta_per_security"],
        wacr_pct=snapshot["wacr_pct"],
        gearing_pct=snapshot["gearing_pct"],
        new_cap_rate_pct=new_cap_rate_pct,
    )
    return result


@app.get("/bond-yields")
def get_bond_yields():
    """Live status of the automated RBA 10-year bond yield feed (full daily
    series available via its 'points' count; see /bond-yields/status for the
    lightweight health check used elsewhere)."""
    series = rba_bond_yields.get_series()
    return {
        "series": series,
        "source": rba_bond_yields.get_status()["source"],
        "source_url": rba_bond_yields.RBA_F2_URL,
    }


@app.get("/bond-yields/status")
def get_bond_yields_status():
    return rba_bond_yields.get_status()


@app.get("/funds/{fund_id}/spread")
def get_spread(fund_id: str):
    """Cap rate risk premium: WACR minus the 10-year govt bond yield, for every
    snapshot of this fund that reports a WACR. Bond yield is the actual daily
    RBA print on (or nearest trading day to) the snapshot's as_of date."""
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    status = rba_bond_yields.get_status()
    points = []
    for snap in fund["snapshots"]:
        if snap["wacr_pct"] is None:
            continue
        bond = rba_bond_yields.nearest(snap["as_of"])
        if bond is None:
            continue
        points.append(
            {
                "period": snap["period"],
                "as_of": snap["as_of"],
                "wacr_pct": snap["wacr_pct"],
                "bond_yield_pct": bond["yield_pct"],
                "bond_yield_period": bond["as_of"],
                "spread_pct": round(snap["wacr_pct"] - bond["yield_pct"], 2),
            }
        )
    points.sort(key=lambda p: p["as_of"])
    return {"fund_id": fund_id, "points": points, "bond_source": status["source"]}


@app.get("/sector-exposure")
def get_sector_exposure():
    return SECTOR_EXPOSURE


@app.get("/risk-ranking")
def get_risk_ranking():
    """Rank every fund with both WACR and gearing by how much its NTA moves
    per +1% cap rate shift — a pure leverage-risk comparison, independent of
    each fund's NTA/unit level."""
    rows = []
    covered_ids = []
    for f in FUNDS:
        snap = f["snapshots"][0]
        if snap["wacr_pct"] is None or snap["gearing_pct"] is None:
            continue
        covered_ids.append(f["id"])
        rows.append(
            {
                "id": f["id"],
                "name": f["name"],
                "ticker": f["ticker"],
                "wacr_pct": snap["wacr_pct"],
                "gearing_pct": snap["gearing_pct"],
                "pct_change_per_1pct_cap_rate_rise": leverage_adjusted_sensitivity(
                    snap["wacr_pct"], snap["gearing_pct"]
                ),
            }
        )
    rows.sort(key=lambda r: r["pct_change_per_1pct_cap_rate_rise"])
    missing = [f["ticker"] for f in FUNDS if f["id"] not in covered_ids]
    return {
        "rows": rows,
        "coverage_note": (
            f"Only funds reporting both WACR and gearing in their latest snapshot are ranked. "
            f"Missing from this ranking: {', '.join(missing)}."
            if missing
            else "All tracked funds are covered."
        ),
    }


@app.get("/funds/{fund_id}/monte-carlo")
def get_monte_carlo(fund_id: str, shift_std_dev_pct: float = 0.5):
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    snapshot = fund["snapshots"][0]
    if snapshot["wacr_pct"] is None or snapshot["gearing_pct"] is None:
        raise HTTPException(
            status_code=422,
            detail="This snapshot is missing WACR or gearing data, so the simulation can't run",
        )

    return monte_carlo_nta(
        nta_per_security=snapshot["nta_per_security"],
        wacr_pct=snapshot["wacr_pct"],
        gearing_pct=snapshot["gearing_pct"],
        shift_std_dev_pct=shift_std_dev_pct,
    )
