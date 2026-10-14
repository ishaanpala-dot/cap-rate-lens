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


def monte_carlo_nta(
    nta_per_security: float,
    wacr_pct: float,
    gearing_pct: float,
    shift_std_dev_pct: float = 0.5,
    simulations: int = 5000,
    seed: int = 42,
) -> MonteCarloResult:
    """Simulate a distribution of NTA outcomes by sampling cap rate shifts from
    a normal distribution centred on the current WACR. shift_std_dev_pct is the
    standard deviation of that shift in percentage points (e.g. 0.5 means cap
    rate moves of +/-0.5pp are a roughly one-standard-deviation outcome) —
    a simplifying assumption, not a fitted volatility estimate, since the
    public data here doesn't carry enough history to estimate real volatility."""
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
    )
