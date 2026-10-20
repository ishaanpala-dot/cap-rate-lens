"""
Cap rate sensitivity model.

Standard income-capitalisation identity: Value = NOI / CapRate.
Holding NOI fixed, a cap rate move from r0 to r1 rescales asset value by (r0 / r1).
Debt is assumed fixed in the short run, so the entire swing in asset value
flows through to equity (NTA) — this is the real mechanic behind why NAV is
more sensitive to cap rate moves than the headline value change suggests,
once you account for gearing.
"""
import numpy as np
from pydantic import BaseModel


class SensitivityResult(BaseModel):
    base_nta_per_security: float
    new_nta_per_security: float
    pct_change: float
    base_cap_rate_pct: float
    new_cap_rate_pct: float
    gearing_pct: float | None


def nta_sensitivity(
    nta_per_security: float,
    wacr_pct: float,
    gearing_pct: float,
    new_cap_rate_pct: float,
) -> SensitivityResult:
    g = gearing_pct / 100
    r0 = wacr_pct / 100
    r1 = new_cap_rate_pct / 100

    assets_per_sec = nta_per_security / (1 - g)
    debt_per_sec = assets_per_sec - nta_per_security

    new_assets_per_sec = assets_per_sec * (r0 / r1)
    new_nta_per_sec = new_assets_per_sec - debt_per_sec

    pct_change = (new_nta_per_sec - nta_per_security) / nta_per_security * 100

    return SensitivityResult(
        base_nta_per_security=round(nta_per_security, 3),
        new_nta_per_security=round(new_nta_per_sec, 3),
        pct_change=round(pct_change, 2),
        base_cap_rate_pct=wacr_pct,
        new_cap_rate_pct=new_cap_rate_pct,
        gearing_pct=gearing_pct,
    )


def leverage_adjusted_sensitivity(wacr_pct: float, gearing_pct: float) -> float:
    """% NTA change per +1% move in cap rate, for ranking funds by leverage risk.
    Pure function of WACR and gearing, independent of NTA level, so it's a fair
    cross-fund comparison even though funds trade at very different NTA/unit."""
    g = gearing_pct / 100
    r0 = wacr_pct / 100
    r1 = r0 + 0.01

    assets = 1 / (1 - g)
    debt = assets - 1
    new_assets = assets * (r0 / r1)
    new_nta = new_assets - debt

    return round((new_nta - 1) * 100, 2)


class CovenantResult(BaseModel):
    gearing_pct: float
    covenant_gearing_pct: float
    cap_rate_at_breach_pct: float
    bp_headroom: float


def covenant_headroom(
    wacr_pct: float,
    gearing_pct: float,
    covenant_gearing_pct: float = 50.0,
) -> CovenantResult:
    """Cap rate rise at which this fund's gearing would reach the given
    threshold, holding debt fixed. None of the funds in this tool disclose an
    actual bank-loan gearing covenant in their headline results, so this uses
    a single assumed threshold applied uniformly to every fund (50% gearing,
    a commonly-cited rule-of-thumb covenant level for Australian REIT debt
    facilities), clearly labelled as an assumption rather than a reported
    figure. Swap in a real disclosed covenant per fund if one is ever sourced.

    Derivation: gearing = Debt / Assets, and Assets scales with cap rate as
    Assets1 = Assets0 * (r0 / r1) (see nta_sensitivity). Debt is fixed, so
    gearing1 = Debt / Assets1 = gearing0 * (Assets0 / Assets1) = gearing0 * (r1 / r0).
    Solving gearing1 = covenant for r1 gives the breach cap rate directly,
    without needing to know Assets or Debt in dollar terms.
    """
    g0 = gearing_pct / 100
    g_target = covenant_gearing_pct / 100
    r0 = wacr_pct

    r1 = r0 * (g_target / g0)
    bp_headroom = (r1 - r0) * 100

    return CovenantResult(
        gearing_pct=gearing_pct,
        covenant_gearing_pct=covenant_gearing_pct,
        cap_rate_at_breach_pct=round(r1, 2),
        bp_headroom=round(bp_headroom, 0),
    )


class HeatmapCell(BaseModel):
    cap_rate_shift_bp: int
    noi_growth_pct: float
    pct_change: float


class HeatmapResult(BaseModel):
    base_nta_per_security: float
    base_cap_rate_pct: float
    cap_rate_shifts_bp: list[int]
    noi_growth_steps_pct: list[float]
    cells: list[HeatmapCell]


def two_factor_heatmap(
    nta_per_security: float,
    wacr_pct: float,
    gearing_pct: float,
) -> HeatmapResult:
    """NTA % change across a grid of cap rate shift x NOI growth, so a reader
    can see what rent growth would be needed to offset a given cap rate move.

    Value = NOI / CapRate. If NOI grows by g and the cap rate moves from r0 to
    r1, new asset value = Assets0 * r0 * (1 + g) / r1 (the (1+g) term is the
    only addition to the plain cap-rate-sensitivity formula). Debt fixed, same
    leverage flow-through as nta_sensitivity."""
    cap_rate_shifts_bp = [-100, -50, -25, 0, 25, 50, 100, 150, 200]
    noi_growth_steps_pct = [-5, -2.5, 0, 2.5, 5, 7.5, 10]

    g = gearing_pct / 100
    r0 = wacr_pct / 100
    assets0 = nta_per_security / (1 - g)
    debt = assets0 - nta_per_security

    cells = []
    for shift_bp in cap_rate_shifts_bp:
        r1 = r0 + shift_bp / 10000
        if r1 <= 0:
            continue
        for noi_growth_pct in noi_growth_steps_pct:
            g_noi = noi_growth_pct / 100
            new_assets = assets0 * r0 * (1 + g_noi) / r1
            new_nta = new_assets - debt
            pct_change = (new_nta - nta_per_security) / nta_per_security * 100
            cells.append(
                HeatmapCell(
                    cap_rate_shift_bp=shift_bp,
                    noi_growth_pct=noi_growth_pct,
                    pct_change=round(pct_change, 1),
                )
            )

    return HeatmapResult(
        base_nta_per_security=round(nta_per_security, 3),
        base_cap_rate_pct=wacr_pct,
        cap_rate_shifts_bp=cap_rate_shifts_bp,
        noi_growth_steps_pct=noi_growth_steps_pct,
        cells=cells,
    )


class MonteCarloResult(BaseModel):
    base_nta_per_security: float
    base_cap_rate_pct: float
    shift_std_dev_pct: float
    simulations: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    calibration: dict | None = None


def monte_carlo_nta(
    nta_per_security: float,
    wacr_pct: float,
    gearing_pct: float,
    shift_std_dev_pct: float = 0.5,
    simulations: int = 5000,
    seed: int = 42,
    calibration: dict | None = None,
) -> MonteCarloResult:
    """Simulate a distribution of NTA outcomes by sampling cap rate shifts from
    a normal distribution centred on the current WACR. shift_std_dev_pct is the
    standard deviation of that shift in percentage points (e.g. 0.5 means cap
    rate moves of +/-0.5pp are a roughly one-standard-deviation outcome).

    When `calibration` is supplied (realised 10-year AGS yield volatility from
    api/rba_bond_yields.py), shift_std_dev_pct should already be set from it by
    the caller, and the dict is carried through on the result so the frontend
    can show exactly how the number was derived rather than asserting it. If
    calibration is None, shift_std_dev_pct is a flat fallback assumption, used
    only if the RBA series couldn't be fetched."""
    rng = np.random.default_rng(seed)
    shifts = rng.normal(loc=0, scale=shift_std_dev_pct, size=simulations)
    simulated_cap_rates = np.clip(wacr_pct + shifts, 0.5, None)

    g = gearing_pct / 100
    r0 = wacr_pct / 100
    assets = nta_per_security / (1 - g)
    debt = assets - nta_per_security

    r1 = simulated_cap_rates / 100
    new_assets = assets * (r0 / r1)
    outcomes = new_assets - debt

    p10, p25, p50, p75, p90 = np.percentile(outcomes, [10, 25, 50, 75, 90])

    return MonteCarloResult(
        base_nta_per_security=round(nta_per_security, 3),
        base_cap_rate_pct=wacr_pct,
        shift_std_dev_pct=shift_std_dev_pct,
        simulations=simulations,
        p10=round(float(p10), 3),
        p25=round(float(p25), 3),
        p50=round(float(p50), 3),
        p75=round(float(p75), 3),
        p90=round(float(p90), 3),
        calibration=calibration,
    )
