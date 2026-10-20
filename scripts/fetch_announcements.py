"""
Phase 1a: automated ingestion of fund results PDFs.

Legal note (checked 2026-10): ASX's own announcements.asx.com.au Terms of Use
explicitly prohibit automated scraping ("any spider, screen scraper, robot...
unless ASX gives prior written consent"), so this deliberately does NOT fetch
from announcements.asx.com.au. It fetches from each fund's own investor
relations page instead, published by the fund for public download, and checks
robots.txt before adding any fund here.

Per-fund automation feasibility (checked 2026-10, see docs/ for detail):
  - Dexus, Mirvac, Stockland, Goodman, Vicinity: permissive robots.txt.
  - GPT Group: permissive robots.txt (standard Drupal boilerplate).
  - Charter Hall: blocked by Cloudflare bot-protection. NOT automatable
    without defeating bot-detection, which this script will never attempt.
    Requires manual/semi-automated handling (as done in-session so far).
  - Scentre Group: JS-rendered Next.js SPA; a plain HTTP fetch of the page
    returns an empty app shell with no PDF links in the HTML. Needs a
    headless-browser fetch to discover links, not implemented here yet.

Only Dexus has a verified, tested IR announcements page URL wired up below.
The other permissive funds (Mirvac, Stockland, Goodman, Vicinity, GPT) need
their exact announcements page URL confirmed before being added here —
guessing a URL risks silently fetching the wrong page or nothing at all.

Usage: python scripts/fetch_announcements.py
Output: scripts/raw_pdfs/<fund_id>/<sha256>.pdf, deduped by content hash,
plus scripts/raw_pdfs/manifest.json tracking what's been fetched.
"""
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx

USER_AGENT = "cap-rate-lens-research/1.0 (+contact: ishaan.pala@gmail.com; for a personal portfolio project, low request volume)"

OUT_DIR = Path(__file__).parent / "raw_pdfs"
MANIFEST_PATH = OUT_DIR / "manifest.json"


@dataclass
class FundSource:
    fund_id: str
    ir_page_url: str
    # Only PDF links whose href or link text matches this pattern are
    # fetched, to avoid pulling distribution notices, tax statements, etc.
    pdf_keyword_pattern: str


# Only funds with a verified working IR page go here. See module docstring
# for the other funds' current automation status.
SOURCES = [
    FundSource(
        fund_id="dxs",
        ir_page_url="https://www.dexus.com/investor-centre/listed-funds/dexus-dxs/results-and-reporting/asx-announcements",
        pdf_keyword_pattern=r"(results|annual-report|half-year|interim)",
    ),
]


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def fetch_pdf_links(source: FundSource) -> list[str]:
    resp = httpx.get(
        source.ir_page_url,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=20,
    )
    resp.raise_for_status()
    hrefs = re.findall(r'href="([^"]*\.pdf[^"]*)"', resp.text)
    pattern = re.compile(source.pdf_keyword_pattern, re.IGNORECASE)
    matched = [h for h in hrefs if pattern.search(h)]
    return [urljoin(source.ir_page_url, h) for h in matched]


def fetch_and_store(source: FundSource, manifest: dict) -> int:
    new_count = 0
    links = fetch_pdf_links(source)
    fund_dir = OUT_DIR / source.fund_id
    fund_dir.mkdir(parents=True, exist_ok=True)
    manifest.setdefault(source.fund_id, {})

    for url in links:
        if url in manifest[source.fund_id]:
            continue  # already fetched this exact URL before

        resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        content = resp.content
        content_hash = hashlib.sha256(content).hexdigest()[:16]

        existing_hashes = {v["hash"] for v in manifest[source.fund_id].values()}
        if content_hash in existing_hashes:
            manifest[source.fund_id][url] = {"hash": content_hash, "status": "duplicate_content"}
            continue

        out_path = fund_dir / f"{content_hash}.pdf"
        out_path.write_bytes(content)
        manifest[source.fund_id][url] = {
            "hash": content_hash,
            "status": "fetched",
            "path": str(out_path.relative_to(OUT_DIR)),
        }
        new_count += 1
        print(f"  fetched: {url} -> {out_path.name}")

    return new_count


def main():
    manifest = load_manifest()
    total_new = 0
    for source in SOURCES:
        print(f"Checking {source.fund_id}...")
        try:
            new_count = fetch_and_store(source, manifest)
            total_new += new_count
            print(f"  {new_count} new file(s)")
        except httpx.HTTPError as e:
            print(f"  FAILED: {e}")
    save_manifest(manifest)
    print(f"\nDone. {total_new} new file(s) across {len(SOURCES)} fund(s) checked.")
    print(f"({8 - len(SOURCES)} tracked funds not yet wired up: see module docstring.)")


if __name__ == "__main__":
    main()
