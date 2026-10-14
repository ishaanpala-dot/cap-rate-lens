import json
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
BOND_YIELDS = json.loads((DATA_DIR / "bond_yields.json").read_text())
SECTOR_EXPOSURE = json.loads((DATA_DIR / "sector_exposure.json").read_text())


def _nearest_bond_yield(as_of: str):
    target = date.fromisoformat(as_of)
    best = min(
        BOND_YIELDS["series"],
        key=lambda p: abs((date.fromisoformat(p["as_of"]) - target).days),
    )
    return best


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/funds")
def list_funds():
    return [{"id": f["id"], "name": f["name"], "ticker": f["ticker"]} for f in FUNDS]


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
            }
        )
    return rows


@app.get("/funds/{fund_id}")
def get_fund(fund_id: str):
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
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
    return BOND_YIELDS


@app.get("/funds/{fund_id}/spread")
def get_spread(fund_id: str):
    """Cap rate risk premium: WACR minus the 10-year govt bond yield, for every
    snapshot of this fund that reports a WACR."""
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    points = []
    for snap in fund["snapshots"]:
        if snap["wacr_pct"] is None:
            continue
        bond = _nearest_bond_yield(snap["as_of"])
        points.append(
            {
                "period": snap["period"],
                "as_of": snap["as_of"],
                "wacr_pct": snap["wacr_pct"],
                "bond_yield_pct": bond["yield_pct"],
                "bond_yield_period": bond["period"],
                "spread_pct": round(snap["wacr_pct"] - bond["yield_pct"], 2),
            }
        )
    points.sort(key=lambda p: p["as_of"])
    return {"fund_id": fund_id, "points": points, "bond_source": BOND_YIELDS["source"]}


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
