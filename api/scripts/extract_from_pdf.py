"""
WORK IN PROGRESS — not wired into the API yet.

Goal: replace the manual "read a quarterly PDF and type numbers into funds.json"
step with an automated extraction pipeline, so the dataset can be kept current
without a person re-reading every fund's results PDF each reporting season.

Planned approach:
  1. Fetch each fund's latest quarterly/half-year results PDF from its ASX
     announcements page (requires a per-fund URL pattern or an ASX announcements
     search).
  2. Extract text per page (pdfplumber or similar).
  3. Use a structured-extraction LLM call (schema: nta_per_security, wacr_pct,
     gearing_pct, wale_years, occupancy_pct, sector breakdown) against the
     relevant pages, since these figures sit in prose/tables that move around
     between funds and reporting periods rather than a fixed layout.
  4. Validate extracted values against sane ranges (e.g. 0 < wacr_pct < 20)
     before writing anything into funds.json, and flag anything that looks
     wrong for manual review rather than silently accepting it.
  5. Append a new snapshot to the relevant fund's "snapshots" array instead of
     overwriting history, so the time-series (spread, trend) features keep
     working.

Not yet implemented:
  - PDF fetching / ASX announcement lookup
  - The actual extraction call
  - Validation and the funds.json merge step

This file is a placeholder marking the intended shape of the pipeline, not a
working script.
"""

raise NotImplementedError("extract_from_pdf.py is a work-in-progress stub, not yet runnable")
