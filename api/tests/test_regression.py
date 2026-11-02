"""
Unit tests for the WACR-vs-gearing cross-sectional regression. Uses small
synthetic fund lists so the expected slope/intercept/R-squared can be
hand-verified, rather than relying on the live dataset (which changes).
"""
import pytest

from regression import wacr_vs_gearing


def _fund(id_, ticker, wacr, gearing):
    return {"id": id_, "ticker": ticker, "snapshots": [{"wacr_pct": wacr, "gearing_pct": gearing}]}


class TestWacrVsGearing:
    def test_perfect_positive_line_gives_r_squared_of_one(self):
        # y = 2x + 1 exactly, for four points — should fit perfectly.
        funds = [
            _fund("a", "A", 3.0, 1.0),
            _fund("b", "B", 5.0, 2.0),
            _fund("c", "C", 7.0, 3.0),
            _fund("d", "D", 9.0, 4.0),
        ]
        result = wacr_vs_gearing(funds)
        assert result.n == 4
        assert result.slope == pytest.approx(2.0, abs=1e-6)
        assert result.intercept == pytest.approx(1.0, abs=1e-6)
        assert result.r_squared == pytest.approx(1.0, abs=1e-6)
        assert result.correlation == pytest.approx(1.0, abs=1e-6)

    def test_excludes_funds_missing_either_figure(self):
        funds = [
            _fund("a", "A", 5.0, 20.0),
            _fund("b", "B", None, 30.0),  # missing WACR
            _fund("c", "C", 6.0, None),  # missing gearing
            _fund("d", "D", 5.5, 25.0),
            _fund("e", "E", 6.5, 35.0),
        ]
        result = wacr_vs_gearing(funds)
        assert result.n == 3
        assert set(result.excluded) == {"B", "C"}
        assert {p.ticker for p in result.points} == {"A", "D", "E"}

    def test_raises_with_fewer_than_three_usable_funds(self):
        funds = [
            _fund("a", "A", 5.0, 20.0),
            _fund("b", "B", 6.0, 30.0),
        ]
        with pytest.raises(ValueError):
            wacr_vs_gearing(funds)

    def test_points_are_sorted_by_x_and_residuals_sum_near_zero(self):
        funds = [
            _fund("a", "A", 6.0, 35.0),
            _fund("b", "B", 5.0, 10.0),
            _fund("c", "C", 5.5, 20.0),
            _fund("d", "D", 6.2, 30.0),
        ]
        result = wacr_vs_gearing(funds)
        xs = [p.x for p in result.points]
        assert xs == sorted(xs)
        # OLS residuals always sum to ~0 by construction.
        assert sum(p.residual for p in result.points) == pytest.approx(0.0, abs=1e-6)

    def test_interpretation_mentions_sample_size_caveat(self):
        funds = [
            _fund("a", "A", 5.0, 20.0),
            _fund("b", "B", 5.5, 25.0),
            _fund("c", "C", 6.0, 30.0),
        ]
        result = wacr_vs_gearing(funds)
        assert str(result.n) in result.interpretation
        assert "suggestive" in result.interpretation.lower()
