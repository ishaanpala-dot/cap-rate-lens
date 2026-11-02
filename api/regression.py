"""
Cross-sectional regression: does a fund's gearing level help explain its
WACR, across the tracked funds at a single point in time?

This is a genuinely different kind of analysis to the rest of the app: those
are all closed-form valuation identities (Value = NOI / CapRate, and what
follows from it), this is a statistical model fitted to observed data, with
all the usual small-sample caveats that implies. It exists to test a
specific hypothesis an analyst would actually ask: do more highly geared
funds trade at wider cap rates (a risk premium for leverage), or is WACR
set independently of balance-sheet structure?

With only 6-8 tracked funds, this is never going to be a confident model.
The honest framing is "here's what a regression on today's small, public
dataset suggests" with the sample size and p-value front and centre, not
"here's the relationship between gearing and cap rates".

Implemented with numpy only (no scipy): simple OLS has a closed-form
solution, and the slope's significance test only needs the t-distribution's
two-tailed survival function, computed here via the regularised incomplete
beta function (the standard way to evaluate the Student's t CDF without a
stats library), not approximated or skipped.
"""
import math

import numpy as np
from pydantic import BaseModel


def _log_beta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical
    Recipes' betacf), used by _reg_incomplete_beta."""
    max_iter = 200
    eps = 3e-12
    fpmin = 1e-300

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break

    return h


def _reg_incomplete_beta(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a, b), via the standard
    continued-fraction evaluation (Numerical Recipes 6.4)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - _log_beta(a, b))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _t_test_two_tailed_p(t_stat: float, deg_free: int) -> float:
    """Two-tailed p-value for a t-statistic with the given degrees of
    freedom, via the Student's t CDF's relation to the incomplete beta
    function: P(|T| > |t|) = I_{df/(df+t^2)}(df/2, 1/2)."""
    if deg_free <= 0:
        return 1.0
    x = deg_free / (deg_free + t_stat**2)
    return _reg_incomplete_beta(deg_free / 2.0, 0.5, x)


class RegressionPoint(BaseModel):
    fund_id: str
    ticker: str
    x: float
    y_actual: float
    y_predicted: float
    residual: float


class RegressionResult(BaseModel):
    n: int
    slope: float
    intercept: float
    r_squared: float
    correlation: float
    p_value: float
    std_err: float
    x_label: str
    y_label: str
    points: list[RegressionPoint]
    excluded: list[str]
    interpretation: str


def wacr_vs_gearing(funds: list[dict]) -> RegressionResult:
    """Simple OLS of latest-snapshot WACR on latest-snapshot gearing, across
    every fund that currently reports both."""
    included: list[tuple[str, str, float, float]] = []
    excluded: list[str] = []

    for f in funds:
        snap = f["snapshots"][0]
        wacr = snap.get("wacr_pct")
        gearing = snap.get("gearing_pct")
        if wacr is None or gearing is None:
            excluded.append(f["ticker"])
            continue
        included.append((f["id"], f["ticker"], gearing, wacr))

    n = len(included)
    if n < 3:
        raise ValueError("Not enough funds with both WACR and gearing to fit a regression")

    xs = np.array([row[2] for row in included], dtype=float)
    ys = np.array([row[3] for row in included], dtype=float)

    x_mean, y_mean = xs.mean(), ys.mean()
    sxx = np.sum((xs - x_mean) ** 2)
    sxy = np.sum((xs - x_mean) * (ys - y_mean))
    syy = np.sum((ys - y_mean) ** 2)

    slope = sxy / sxx
    intercept = y_mean - slope * x_mean

    y_hat = slope * xs + intercept
    residuals = ys - y_hat
    ss_res = np.sum(residuals**2)
    r_squared = 1 - ss_res / syy if syy > 0 else 0.0
    correlation = sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else 0.0

    deg_free = n - 2
    if deg_free > 0 and ss_res > 0:
        residual_std_err = math.sqrt(ss_res / deg_free)
        slope_std_err = residual_std_err / math.sqrt(sxx)
        t_stat = slope / slope_std_err if slope_std_err > 0 else 0.0
        p_value = _t_test_two_tailed_p(t_stat, deg_free)
    else:
        slope_std_err = 0.0
        p_value = 1.0

    points = []
    for (fund_id, ticker, x, y), yhat, resid in zip(included, y_hat, residuals):
        points.append(
            RegressionPoint(
                fund_id=fund_id,
                ticker=ticker,
                x=round(float(x), 2),
                y_actual=round(float(y), 3),
                y_predicted=round(float(yhat), 3),
                residual=round(float(resid), 3),
            )
        )
    points.sort(key=lambda p: p.x)

    direction = "higher" if slope > 0 else "lower"
    significance = (
        "statistically significant at the 5% level"
        if p_value < 0.05
        else "not statistically significant at the 5% level"
    )
    interpretation = (
        f"Across the {n} tracked funds reporting both figures, each additional "
        f"percentage point of gearing is associated with a {abs(slope):.3f}pp "
        f"{direction} WACR on this fit, {significance} (p={p_value:.2f}). "
        f"With only {n} data points, this result is suggestive at best, not a "
        f"reliable estimate, treat it as a starting hypothesis, not a finding."
    )

    return RegressionResult(
        n=n,
        slope=round(float(slope), 4),
        intercept=round(float(intercept), 4),
        r_squared=round(float(r_squared), 4),
        correlation=round(float(correlation), 4),
        p_value=round(float(p_value), 4),
        std_err=round(float(slope_std_err), 4),
        x_label="Gearing (%)",
        y_label="WACR (%)",
        points=points,
        excluded=excluded,
        interpretation=interpretation,
    )
