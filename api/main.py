import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import rba_bond_yields
from valuation import (
    covenant_headroom,
    leverage_adjusted_sensitivity,
    monte_carlo_nta,
    nta_sensitivity,
    two_factor_heatmap,
)

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
                "source": snap.get("source"),
                "source_url": snap.get("source_url"),
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
def get_monte_carlo(fund_id: str, shift_std_dev_pct: float | None = None):
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    snapshot = fund["snapshots"][0]
    if snapshot["wacr_pct"] is None or snapshot["gearing_pct"] is None:
        raise HTTPException(
            status_code=422,
            detail="This snapshot is missing WACR or gearing data, so the simulation can't run",
        )

    calibration = None
    std_dev = shift_std_dev_pct
    if std_dev is None:
        vol = rba_bond_yields.historical_volatility()
        if vol is not None:
            std_dev = vol["annualised_std_dev_pct"]
            calibration = vol
        else:
            std_dev = 0.5  # fallback if the RBA series is unavailable

    return monte_carlo_nta(
        nta_per_security=snapshot["nta_per_security"],
        wacr_pct=snapshot["wacr_pct"],
        gearing_pct=snapshot["gearing_pct"],
        shift_std_dev_pct=std_dev,
        calibration=calibration,
    )


@app.get("/funds/{fund_id}/covenant")
def get_covenant(fund_id: str, covenant_gearing_pct: float = 50.0):
    """Cap rate rise at which this fund's gearing would reach an assumed
    covenant threshold. See valuation.covenant_headroom for the honesty note:
    no fund here discloses an actual bank covenant, so this is a single
    assumption applied uniformly, not a per-fund reported figure."""
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    snapshot = fund["snapshots"][0]
    if snapshot["wacr_pct"] is None or snapshot["gearing_pct"] is None:
        raise HTTPException(
            status_code=422,
            detail="This snapshot is missing WACR or gearing data, so covenant headroom can't be computed",
        )

    return covenant_headroom(
        wacr_pct=snapshot["wacr_pct"],
        gearing_pct=snapshot["gearing_pct"],
        covenant_gearing_pct=covenant_gearing_pct,
    )


@app.get("/covenant-ranking")
def get_covenant_ranking(covenant_gearing_pct: float = 50.0):
    """Every covered fund ranked by headroom (in bp of cap rate rise) to the
    same assumed covenant threshold, least headroom first."""
    rows = []
    covered_ids = []
    for f in FUNDS:
        snap = f["snapshots"][0]
        if snap["wacr_pct"] is None or snap["gearing_pct"] is None:
            continue
        covered_ids.append(f["id"])
        result = covenant_headroom(snap["wacr_pct"], snap["gearing_pct"], covenant_gearing_pct)
        rows.append(
            {
                "id": f["id"],
                "name": f["name"],
                "ticker": f["ticker"],
                "gearing_pct": snap["gearing_pct"],
                "bp_headroom": result.bp_headroom,
                "cap_rate_at_breach_pct": result.cap_rate_at_breach_pct,
            }
        )
    rows.sort(key=lambda r: r["bp_headroom"])
    missing = [f["ticker"] for f in FUNDS if f["id"] not in covered_ids]
    return {
        "covenant_gearing_pct": covenant_gearing_pct,
        "rows": rows,
        "assumption_note": (
            f"No tracked fund discloses an actual bank-loan gearing covenant in its headline "
            f"results. This uses a single assumed {covenant_gearing_pct:.0f}% gearing threshold "
            f"applied uniformly to every fund, not a reported figure."
        ),
        "coverage_note": (
            f"Missing from this ranking: {', '.join(missing)}." if missing else "All tracked funds are covered."
        ),
    }


@app.get("/funds/{fund_id}/heatmap")
def get_heatmap(fund_id: str):
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    snapshot = fund["snapshots"][0]
    if snapshot["wacr_pct"] is None or snapshot["gearing_pct"] is None:
        raise HTTPException(
            status_code=422,
            detail="This snapshot is missing WACR or gearing data, so the heatmap can't be computed",
        )

    return two_factor_heatmap(
        nta_per_security=snapshot["nta_per_security"],
        wacr_pct=snapshot["wacr_pct"],
        gearing_pct=snapshot["gearing_pct"],
    )


@app.get("/funds/{fund_id}/commentary")
def get_commentary(fund_id: str):
    """Deterministic plain-English summary built entirely from templates
    filled with already-computed numbers, never free-form generated text, so
    it can't hallucinate a figure that isn't backed by the data above."""
    fund = FUNDS_BY_ID.get(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    snap = fund["snapshots"][0]
    sentences: list[str] = []

    covered = [
        {"id": f["id"], "ticker": f["ticker"], "gearing": f["snapshots"][0]["gearing_pct"]}
        for f in FUNDS
        if f["snapshots"][0]["gearing_pct"] is not None
    ]
    if snap["gearing_pct"] is not None and len(covered) > 1:
        sorted_by_gearing = sorted(covered, key=lambda r: r["gearing"])
        rank = next(i for i, r in enumerate(sorted_by_gearing) if r["id"] == fund["id"])
        percentile = round((rank / (len(sorted_by_gearing) - 1)) * 100)
        quartile = (
            "lowest quartile" if percentile <= 25
            else "top quartile" if percentile >= 75
            else "middle of the range"
        )
        sentences.append(
            f"Gearing of {snap['gearing_pct']:.1f}% is in the {quartile} among the "
            f"{len(covered)} tracked funds that report it."
        )

    if snap["wacr_pct"] is not None:
        bond = rba_bond_yields.nearest(snap["as_of"])
        if bond is not None:
            spread = round(snap["wacr_pct"] - bond["yield_pct"], 2)
            direction = "above" if spread >= 0 else "below"
            sentences.append(
                f"WACR of {snap['wacr_pct']:.2f}% sits {abs(spread):.2f}pp {direction} the "
                f"10-year government bond yield ({bond['yield_pct']:.2f}% as of {bond['as_of']})."
            )

    if snap["wacr_pct"] is not None and snap["gearing_pct"] is not None:
        sens = leverage_adjusted_sensitivity(snap["wacr_pct"], snap["gearing_pct"])
        ranked = sorted(
            (
                {"id": f["id"], "ticker": f["ticker"], "sens": leverage_adjusted_sensitivity(
                    f["snapshots"][0]["wacr_pct"], f["snapshots"][0]["gearing_pct"]
                )}
                for f in FUNDS
                if f["snapshots"][0]["wacr_pct"] is not None and f["snapshots"][0]["gearing_pct"] is not None
            ),
            key=lambda r: r["sens"],
        )
        rank = next(i for i, r in enumerate(ranked) if r["id"] == fund["id"]) + 1
        suffix = "th" if 11 <= rank % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
        sentences.append(
            f"A +100bp rise in cap rate would reduce NTA per security by {abs(sens):.1f}%, "
            f"the {rank}{suffix} most leverage-sensitive of {len(ranked)} tracked funds."
        )

        covenant = covenant_headroom(snap["wacr_pct"], snap["gearing_pct"])
        sentences.append(
            f"Under an assumed 50% gearing threshold (not a disclosed covenant), cap rate "
            f"would need to rise {covenant.bp_headroom:.0f}bp from here to reach it."
        )

    return {"fund_id": fund_id, "sentences": sentences}


class PortfolioHolding(BaseModel):
    fund_id: str
    amount: float


class PortfolioRequest(BaseModel):
    holdings: list[PortfolioHolding]


@app.post("/portfolio")
def post_portfolio(req: PortfolioRequest):
    """Aggregate a user-entered set of holdings (fund_id + dollar amount) into
    a combined gearing, a combined sensitivity curve, and combined sector
    exposure where available. Cap rate shocks are applied uniformly across all
    holdings (i.e. assumes every fund's cap rate moves together) — a
    simplification stated here rather than hidden; modelling fund-specific or
    correlated shocks is future work, not implemented."""
    if not req.holdings:
        raise HTTPException(status_code=422, detail="Provide at least one holding")

    rows = []
    total = 0.0
    weighted_gearing_sum = 0.0
    weighted_wacr_sum = 0.0
    modelled_total = 0.0
    sector_totals: dict[str, float] = {}
    sector_coverage_total = 0.0

    for h in req.holdings:
        fund = FUNDS_BY_ID.get(h.fund_id)
        if not fund:
            raise HTTPException(status_code=404, detail=f"Unknown fund_id: {h.fund_id}")
        if h.amount <= 0:
            raise HTTPException(status_code=422, detail=f"Amount for {h.fund_id} must be positive")

        snap = fund["snapshots"][0]
        total += h.amount
        rows.append({"id": fund["id"], "ticker": fund["ticker"], "amount": h.amount})

        if snap["gearing_pct"] is not None:
            weighted_gearing_sum += h.amount * snap["gearing_pct"]
        if snap["wacr_pct"] is not None:
            weighted_wacr_sum += h.amount * snap["wacr_pct"]
            if snap["gearing_pct"] is not None:
                modelled_total += h.amount

        exposure = next((e for e in SECTOR_EXPOSURE["funds"] if e["id"] == fund["id"]), None)
        if exposure:
            sector_coverage_total += h.amount
            for s in exposure["sectors"]:
                sector_totals[s["sector"]] = sector_totals.get(s["sector"], 0) + h.amount * (s["pct"] / 100)

    weighted_gearing = round(weighted_gearing_sum / total, 1) if total else None
    weighted_wacr = round(weighted_wacr_sum / total, 2) if total else None

    shifts_bp = [-100, -50, -25, 0, 25, 50, 100, 150, 200]
    curve = []
    for shift_bp in shifts_bp:
        combined_dollar_change = 0.0
        for h in req.holdings:
            fund = FUNDS_BY_ID[h.fund_id]
            snap = fund["snapshots"][0]
            if snap["wacr_pct"] is None or snap["gearing_pct"] is None:
                continue
            new_rate = snap["wacr_pct"] + shift_bp / 100
            if new_rate <= 0:
                continue
            result = nta_sensitivity(1.0, snap["wacr_pct"], snap["gearing_pct"], new_rate)
            combined_dollar_change += h.amount * (result.pct_change / 100)
        pct_change = round((combined_dollar_change / modelled_total) * 100, 2) if modelled_total else None
        curve.append({"cap_rate_shift_bp": shift_bp, "pct_change": pct_change})

    sector_exposure = (
        [
            {"sector": s, "pct": round((amt / sector_coverage_total) * 100, 1)}
            for s, amt in sorted(sector_totals.items(), key=lambda kv: -kv[1])
        ]
        if sector_coverage_total > 0
        else []
    )

    return {
        "holdings": rows,
        "total_amount": total,
        "weighted_gearing_pct": weighted_gearing,
        "weighted_wacr_pct": weighted_wacr,
        "modelled_amount": modelled_total,
        "modelled_coverage_pct": round((modelled_total / total) * 100, 1) if total else None,
        "sensitivity_curve": curve,
        "sector_exposure": sector_exposure,
        "sector_exposure_coverage_pct": round((sector_coverage_total / total) * 100, 1) if total else None,
        "note": (
            "Cap rate shocks are applied uniformly across all holdings (every fund's cap rate "
            "moves by the same amount in this model) — a simplification, not a joint/correlated "
            "simulation. Sector exposure and the sensitivity curve only cover holdings with the "
            "relevant data sourced; coverage percentages are stated above."
        ),
    }
