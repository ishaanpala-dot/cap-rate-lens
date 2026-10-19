"""
Automated fetch of the RBA's daily 10-year Australian Government bond yield
(table F2, series FCMYGBAG10D), replacing the manual single-point figure we
started with. This is the first piece of the automated data pipeline described
in docs/cap-rate-lens-upgrade-prompt.md (Phase 1c).

Source: https://www.rba.gov.au/statistics/tables/csv/f2-data.csv
Public, free, no API key, no rate-limit terms beyond normal fair use. We cache
in memory and only refetch when the cache goes stale, rather than hitting RBA
on every request.
"""
import csv
import io
import time
from datetime import date, datetime

import httpx

RBA_F2_URL = "https://www.rba.gov.au/statistics/tables/csv/f2-data.csv"
CACHE_TTL_SECONDS = 12 * 60 * 60  # refetch at most twice a day

_cache: dict = {"series": None, "fetched_at": 0.0, "error": None}


def _parse_f2_csv(text: str) -> list[dict]:
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    # Series ID row tells us which column is the 10-year yield; don't hardcode
    # a column index in case RBA reorders columns in a future export.
    series_id_row = next((r for r in rows if r and r[0] == "Series ID"), None)
    if not series_id_row:
        raise ValueError("Could not find 'Series ID' row in RBA F2 CSV")
    try:
        col_10y = series_id_row.index("FCMYGBAG10D")
    except ValueError as e:
        raise ValueError("FCMYGBAG10D (10-year yield) column not found in RBA F2 CSV") from e

    out = []
    for row in rows:
        if not row or not row[0]:
            continue
        try:
            d = datetime.strptime(row[0], "%d-%b-%Y").date()
        except ValueError:
            continue  # header/metadata rows
        if col_10y >= len(row) or not row[col_10y]:
            continue
        try:
            yield_pct = float(row[col_10y])
        except ValueError:
            continue
        out.append({"as_of": d.isoformat(), "yield_pct": yield_pct})

    out.sort(key=lambda r: r["as_of"])
    return out


def get_series() -> list[dict]:
    """Full daily 10-year AGS yield series, cached. Returns the stale cache
    (or an empty list, never raises) if the live fetch fails, so a transient
    RBA outage can't take down the app."""
    now = time.time()
    if _cache["series"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return _cache["series"]

    try:
        resp = httpx.get(RBA_F2_URL, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        series = _parse_f2_csv(resp.text)
        if not series:
            raise ValueError("Parsed RBA F2 CSV but found zero valid rows")
        _cache["series"] = series
        _cache["fetched_at"] = now
        _cache["error"] = None
    except Exception as e:  # noqa: BLE001 - deliberately broad: never crash the app on a data-source hiccup
        _cache["error"] = str(e)
        if _cache["series"] is None:
            return []

    return _cache["series"]


def get_status() -> dict:
    series = get_series()
    return {
        "source": "RBA statistical table F2, series FCMYGBAG10D (10-year Australian Government bond yield, daily)",
        "source_url": RBA_F2_URL,
        "points": len(series),
        "earliest": series[0]["as_of"] if series else None,
        "latest": series[-1]["as_of"] if series else None,
        "cache_fetched_at": (
            datetime.fromtimestamp(_cache["fetched_at"]).isoformat() if _cache["fetched_at"] else None
        ),
        "last_error": _cache["error"],
    }


def nearest(as_of: str) -> dict | None:
    series = get_series()
    if not series:
        return None
    target = date.fromisoformat(as_of)
    return min(series, key=lambda p: abs((date.fromisoformat(p["as_of"]) - target).days))
