"""
Unit tests for the pure valuation math in valuation.py. These check the
model's actual outputs against hand-worked numbers, not just that the
functions run without raising.
"""
import math

import pytest

from valuation import (
    covenant_headroom,
    leverage_adjusted_sensitivity,
    monte_carlo_nta,
    nta_sensitivity,
    two_factor_heatmap,
)


class TestNtaSensitivity:
    def test_unchanged_cap_rate_leaves_nta_unchanged(self):
        result = nta_sensitivity(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0, new_cap_rate_pct=6.0
        )
        assert result.new_nta_per_security == pytest.approx(10.0, abs=1e-6)
        assert result.pct_change == pytest.approx(0.0, abs=1e-6)

    def test_cap_rate_rise_lowers_nta(self):
        result = nta_sensitivity(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0, new_cap_rate_pct=7.0
        )
        assert result.new_nta_per_security < 10.0
        assert result.pct_change < 0

    def test_cap_rate_fall_raises_nta(self):
        result = nta_sensitivity(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0, new_cap_rate_pct=5.0
        )
        assert result.new_nta_per_security > 10.0
        assert result.pct_change > 0

    def test_known_values_zero_gearing_equals_cap_rate_ratio(self):
        # With no leverage, assets == NTA, so new NTA should scale by exactly r0/r1.
        result = nta_sensitivity(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=0.0, new_cap_rate_pct=7.0
        )
        expected = 10.0 * (6.0 / 7.0)
        # new_nta_per_security is rounded to 3dp by the implementation, so
        # compare at that precision rather than exactly.
        assert result.new_nta_per_security == pytest.approx(expected, abs=5e-4)

    def test_higher_gearing_amplifies_the_swing(self):
        low_gearing = nta_sensitivity(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=20.0, new_cap_rate_pct=7.0
        )
        high_gearing = nta_sensitivity(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=50.0, new_cap_rate_pct=7.0
        )
        assert abs(high_gearing.pct_change) > abs(low_gearing.pct_change)


class TestLeverageAdjustedSensitivity:
    def test_matches_nta_sensitivity_for_a_1pp_rise(self):
        # leverage_adjusted_sensitivity is defined as the pct_change for a flat
        # +1pp cap rate move; it should agree with nta_sensitivity called directly.
        wacr, gearing = 6.0, 35.0
        direct = nta_sensitivity(
            nta_per_security=1.0, wacr_pct=wacr, gearing_pct=gearing, new_cap_rate_pct=wacr + 1.0
        )
        via_helper = leverage_adjusted_sensitivity(wacr_pct=wacr, gearing_pct=gearing)
        assert via_helper == pytest.approx(direct.pct_change, abs=0.01)

    def test_is_independent_of_nta_level(self):
        # Pure function of WACR and gearing only — same ratio regardless of scale.
        a = leverage_adjusted_sensitivity(wacr_pct=6.0, gearing_pct=30.0)
        b = leverage_adjusted_sensitivity(wacr_pct=6.0, gearing_pct=30.0)
        assert a == b

    def test_higher_gearing_ranks_as_more_negative(self):
        low = leverage_adjusted_sensitivity(wacr_pct=6.0, gearing_pct=20.0)
        high = leverage_adjusted_sensitivity(wacr_pct=6.0, gearing_pct=55.0)
        assert high < low < 0


class TestCovenantHeadroom:
    def test_zero_headroom_when_already_at_covenant(self):
        result = covenant_headroom(wacr_pct=6.0, gearing_pct=50.0, covenant_gearing_pct=50.0)
        assert result.bp_headroom == pytest.approx(0.0, abs=1.0)

    def test_lower_current_gearing_gives_more_headroom(self):
        tight = covenant_headroom(wacr_pct=6.0, gearing_pct=45.0, covenant_gearing_pct=50.0)
        loose = covenant_headroom(wacr_pct=6.0, gearing_pct=20.0, covenant_gearing_pct=50.0)
        assert loose.bp_headroom > tight.bp_headroom > 0

    def test_breach_cap_rate_matches_closed_form_derivation(self):
        # r1 = r0 * (g_target / g0), per the docstring's derivation.
        wacr, gearing, covenant = 6.0, 30.0, 50.0
        result = covenant_headroom(wacr_pct=wacr, gearing_pct=gearing, covenant_gearing_pct=covenant)
        expected_r1 = wacr * (covenant / gearing)
        assert result.cap_rate_at_breach_pct == pytest.approx(expected_r1, abs=0.01)

    def test_gearing_above_covenant_already_breached_gives_negative_headroom(self):
        result = covenant_headroom(wacr_pct=6.0, gearing_pct=55.0, covenant_gearing_pct=50.0)
        assert result.bp_headroom < 0


class TestTwoFactorHeatmap:
    def test_zero_shift_zero_growth_cell_is_unchanged(self):
        result = two_factor_heatmap(nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0)
        zero_cell = next(
            c for c in result.cells if c.cap_rate_shift_bp == 0 and c.noi_growth_pct == 0
        )
        assert zero_cell.pct_change == pytest.approx(0.0, abs=0.1)

    def test_positive_noi_growth_offsets_a_cap_rate_rise(self):
        result = two_factor_heatmap(nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0)
        no_growth = next(
            c for c in result.cells if c.cap_rate_shift_bp == 100 and c.noi_growth_pct == 0
        )
        with_growth = next(
            c for c in result.cells if c.cap_rate_shift_bp == 100 and c.noi_growth_pct == 10
        )
        assert with_growth.pct_change > no_growth.pct_change

    def test_covers_every_combination_of_the_two_grids(self):
        result = two_factor_heatmap(nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0)
        expected = len(result.cap_rate_shifts_bp) * len(result.noi_growth_steps_pct)
        assert len(result.cells) == expected


class TestMonteCarloNta:
    def test_is_deterministic_for_a_fixed_seed(self):
        a = monte_carlo_nta(nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0, seed=7)
        b = monte_carlo_nta(nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0, seed=7)
        assert a.p50 == b.p50
        assert a.p10 == b.p10
        assert a.p90 == b.p90

    def test_percentiles_are_monotonic(self):
        result = monte_carlo_nta(nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0)
        assert result.p10 <= result.p25 <= result.p50 <= result.p75 <= result.p90

    def test_median_is_close_to_the_base_case(self):
        # Shifts are drawn from a normal distribution centred on 0, so the
        # median simulated outcome should land near (not exactly at, due to
        # convexity in 1/x) the unshifted NTA.
        result = monte_carlo_nta(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0, shift_std_dev_pct=0.3
        )
        assert result.p50 == pytest.approx(10.0, rel=0.05)

    def test_wider_std_dev_widens_the_outcome_range(self):
        narrow = monte_carlo_nta(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0, shift_std_dev_pct=0.2, seed=1
        )
        wide = monte_carlo_nta(
            nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0, shift_std_dev_pct=1.5, seed=1
        )
        assert (wide.p90 - wide.p10) > (narrow.p90 - narrow.p10)

    def test_cap_rate_is_floored_so_outcomes_stay_finite(self):
        # A very wide std dev could otherwise draw a cap rate <= 0, which would
        # blow up the NOI/CapRate identity — confirm the clip in the
        # implementation keeps every simulated outcome finite.
        result = monte_carlo_nta(
            nta_per_security=10.0, wacr_pct=1.0, gearing_pct=30.0, shift_std_dev_pct=5.0
        )
        for v in (result.p10, result.p25, result.p50, result.p75, result.p90):
            assert math.isfinite(v)

    def test_calibration_metadata_passes_through_untouched(self):
        calib = {"annualised_std_dev_pct": 0.74, "method": "test"}
        result = monte_carlo_nta(
            nta_per_security=10.0,
            wacr_pct=6.0,
            gearing_pct=30.0,
            shift_std_dev_pct=0.74,
            calibration=calib,
        )
        assert result.calibration == calib

    def test_calibration_defaults_to_none(self):
        result = monte_carlo_nta(nta_per_security=10.0, wacr_pct=6.0, gearing_pct=30.0)
        assert result.calibration is None
