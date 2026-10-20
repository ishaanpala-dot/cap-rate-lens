"""
Unit tests for rba_bond_yields.py: the F2 CSV parser and the realised-
volatility calibration used by the Monte Carlo simulation. These never hit
the network — the cache is monkeypatched directly with synthetic series so
the tests are deterministic and don't depend on RBA's live data changing.
"""
from datetime import date, timedelta

import pytest

import rba_bond_yields as rba


SAMPLE_F2_CSV = """Title,Interest rates and yields – money market – daily
Description,Cash rate target; interest rates; ...
Frequency,Daily
Type,Original
Units,Per cent per annum
Source,RBA
Publication date,20 Oct 2026
Series ID,FIRMMCRTD,FCMYGBAG2D,FCMYGBAG10D
01-Jan-2026,4.10,3.20,4.50
02-Jan-2026,4.10,3.22,4.53
05-Jan-2026,4.10,,4.49
06-Jan-2026,4.10,3.19,4.55
"""


class TestParseF2Csv:
    def test_extracts_the_10y_column_by_series_id_not_position(self):
        rows = rba._parse_f2_csv(SAMPLE_F2_CSV)
        assert rows == [
            {"as_of": "2026-01-01", "yield_pct": 4.50},
            {"as_of": "2026-01-02", "yield_pct": 4.53},
            {"as_of": "2026-01-05", "yield_pct": 4.49},
            {"as_of": "2026-01-06", "yield_pct": 4.55},
        ]

    def test_skips_rows_with_a_blank_value_in_the_target_column(self):
        csv_with_gap = SAMPLE_F2_CSV.replace("05-Jan-2026,4.10,,4.49", "05-Jan-2026,4.10,3.19,")
        rows = rba._parse_f2_csv(csv_with_gap)
        dates = [r["as_of"] for r in rows]
        assert "2026-01-05" not in dates
        assert len(rows) == 3

    def test_output_is_sorted_by_date(self):
        # Swap two data rows so the raw file is out of order; parser must still sort.
        lines = SAMPLE_F2_CSV.splitlines()
        lines[-2], lines[-1] = lines[-1], lines[-2]
        shuffled = "\n".join(lines)
        rows = rba._parse_f2_csv(shuffled)
        assert [r["as_of"] for r in rows] == sorted(r["as_of"] for r in rows)

    def test_missing_series_id_raises(self):
        broken = "Title,x\n01-Jan-2026,4.1\n"
        with pytest.raises(ValueError, match="Series ID"):
            rba._parse_f2_csv(broken)

    def test_missing_target_series_raises(self):
        no_10y = SAMPLE_F2_CSV.replace("FCMYGBAG10D", "SOME_OTHER_SERIES")
        with pytest.raises(ValueError, match="FCMYGBAG10D"):
            rba._parse_f2_csv(no_10y)


class TestHistoricalVolatility:
    def _set_series(self, monkeypatch, values):
        start = date(2026, 1, 1)
        series = [
            {"as_of": (start + timedelta(days=i)).isoformat(), "yield_pct": v}
            for i, v in enumerate(values)
        ]
        monkeypatch.setattr(rba, "get_series", lambda: series)

    def test_none_when_fewer_than_31_observations(self, monkeypatch):
        self._set_series(monkeypatch, [4.5] * 20)
        assert rba.historical_volatility() is None

    def test_zero_volatility_for_a_flat_series(self, monkeypatch):
        self._set_series(monkeypatch, [4.5] * 40)
        result = rba.historical_volatility()
        assert result is not None
        assert result["annualised_std_dev_pct"] == pytest.approx(0.0, abs=1e-9)

    def test_matches_hand_computed_std_dev_for_a_simple_alternating_series(self, monkeypatch):
        # Alternating +0.1/-0.1 day-over-day changes have a known population std dev;
        # confirm the annualisation scaling (sqrt(252)) is applied correctly.
        values = [4.5]
        for i in range(39):
            values.append(values[-1] + (0.1 if i % 2 == 0 else -0.1))
        self._set_series(monkeypatch, values)

        result = rba.historical_volatility()
        assert result is not None

        import numpy as np

        diffs = np.diff(np.array(values))
        expected_daily_std = float(np.std(diffs, ddof=1))
        expected_annualised = expected_daily_std * (252 ** 0.5)

        assert result["daily_std_dev_pct"] == pytest.approx(expected_daily_std, abs=1e-4)
        assert result["annualised_std_dev_pct"] == pytest.approx(expected_annualised, abs=1e-3)

    def test_uses_only_the_trailing_window(self, monkeypatch):
        # A volatile stretch outside the window should not affect the result.
        calm = [4.5] * 300
        volatile = [4.5 + (1.0 if i % 2 == 0 else -1.0) for i in range(50)]
        self._set_series(monkeypatch, volatile + calm)

        result = rba.historical_volatility(window_days=252)
        assert result is not None
        assert result["annualised_std_dev_pct"] == pytest.approx(0.0, abs=1e-6)

    def test_reports_window_bounds_and_sample_size(self, monkeypatch):
        self._set_series(monkeypatch, [4.5 + 0.01 * i for i in range(40)])
        result = rba.historical_volatility()
        assert result["n_daily_changes"] == 39
        assert result["window_start"] == "2026-01-01"
        assert result["window_end"] == "2026-02-09"
