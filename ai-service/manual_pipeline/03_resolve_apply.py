"""
resolve_apply_links.py — Direct Career Portal & Apply Link Resolver

Takes matched jobs from top_matches.json (or matched_jobs_ranked.csv) and:
1. Strips aggregator tracking parameters (utm, refId, trackingId, etc.).
2. Resolves redirects for aggregator URLs to find the actual ATS / company career page.
3. Detects the underlying ATS platform (Greenhouse, Lever, Workday, SmartRecruiters, Ashby, LinkedIn, Indeed, etc.).
4. Outputs clean direct application links for one-click manual applying.

Outputs:
    resolved_apply_links.csv
    resolved_apply_links.json
"""

import json
import re
import urllib.parse
from pathlib import Path
import pandas as pd
import requests
import config

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

INPUT_JSON  = str(config.TOP_MATCHES_JSON)
INPUT_CSV   = str(config.MATCHED_JOBS_CSV)
OUTPUT_CSV  = str(config.RESOLVED_APPLY_CSV)
OUTPUT_JSON = str(config.RESOLVED_APPLY_JSON)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Known ATS domains
ATS_SIGNATURES = {
    "greenhouse.io": "Greenhouse",
    "lever.co": "Lever",
    "myworkdayjobs.com": "Workday",
    "smartrecruiters.com": "SmartRecruiters",
    "ashbyhq.com": "Ashby",
    "taleo.net": "Taleo",
    "icims.com": "iCIMS",
    "bamboohr.com": "BambooHR",
    "workable.com": "Workable",
    "darwinbox.in": "Darwinbox",
    "keka.com": "Keka",
    "recruitee.com": "Recruitee",
    "linkedin.com": "LinkedIn",
    "indeed.com": "Indeed",
}

def clean_url(url: str) -> str:
    """Strip unnecessary tracking query parameters from URL."""
    if not isinstance(url, str) or not url.strip():
        return ""
    
    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        # Drop tracking query params
        tracking_keys = {
            "refid", "trackingid", "currentjobid", "ebp", "origin", 
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "from", "vjs", "trk", "trkinfo"
        }
        query_dict = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        cleaned_query = {k: v for k, v in query_dict.items() if k.lower() not in tracking_keys}
        
        # Re-encode query
        new_query = urllib.parse.urlencode(cleaned_query, doseq=True)
        cleaned = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        return cleaned.rstrip("?")
    except Exception:
        return url

def detect_ats_platform(url: str) -> str:
    """Identify which ATS or job platform the link points to."""
    if not url:
        return "Unknown"
    domain = urllib.parse.urlparse(url).netloc.lower()
    for sig, name in ATS_SIGNATURES.items():
        if sig in domain:
            return name
    return "Direct Career Portal"

def resolve_redirect(url: str, timeout: int = 5) -> tuple[str, str]:
    """
    Follow HTTP redirects to unmask destination ATS links.
    Returns (resolved_url, ats_name).
    """
    cleaned = clean_url(url)
    if not cleaned:
        return "", "Unknown"

    ats = detect_ats_platform(cleaned)
    # If already a direct ATS or clean LinkedIn link, return directly
    if ats not in ["Indeed", "Unknown"]:
        return cleaned, ats

    # If it's an aggregator redirect (e.g. indeed.com/job/...)
    try:
        resp = requests.head(cleaned, headers=HEADERS, allow_redirects=True, timeout=timeout)
        final_url = clean_url(resp.url)
        return final_url, detect_ats_platform(final_url)
    except Exception:
        # Fallback to cleaned URL if redirect lookup fails/times out
        return cleaned, ats

def main():
    print("=" * 70)
    print("🔗 Resolve Direct Apply Links & Career Portals")
    print("=" * 70)

    # 1. Load data
    jobs = []
    if Path(INPUT_JSON).exists():
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        print(f"Loaded {len(jobs)} jobs from {INPUT_JSON}")
    elif Path(INPUT_CSV).exists():
        df = pd.read_csv(INPUT_CSV)
        jobs = df.head(25).to_dict(orient="records")
        print(f"Loaded {len(jobs)} jobs from {INPUT_CSV}")
    else:
        print("No matched jobs file found. Please run match_jobs.py first.")
        return

    # 2. Resolve URLs
    resolved_records = []
    print("\nResolving links and identifying ATS platforms...")
    for idx, job in enumerate(jobs, start=1):
        raw_url = job.get("job_url", "")
        company = job.get("company", "Unknown")
        title   = job.get("title", "Role")
        score   = round(float(job.get("match_score", 0.0)), 1)
        location = job.get("location", "India")

        resolved_url, ats_platform = resolve_redirect(raw_url)

        record = {
            "rank": job.get("rank", idx),
            "match_score": score,
            "title": title,
            "company": company,
            "location": location,
            "ats_platform": ats_platform,
            "clean_apply_url": resolved_url or raw_url,
            "portal_view_url": clean_url(raw_url),
        }
        resolved_records.append(record)

    # 3. Save outputs
    out_df = pd.DataFrame(resolved_records)
    out_df.to_csv(OUTPUT_CSV, index=False)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resolved_records, f, indent=2)

    print(f"\n✅ Saved {len(resolved_records)} resolved apply links to:")
    print(f"   - {OUTPUT_CSV}")
    print(f"   - {OUTPUT_JSON}")

    # 4. Display Table
    print("\n" + "=" * 100)
    print(f"{'Rank':<5} {'Score':<7} {'Company':<24} {'Platform':<15} {'Direct Apply URL'}")
    print("-" * 100)
    for r in resolved_records[:15]:
        comp = str(r['company'])[:22]
        plat = str(r['ats_platform'])[:13]
        url_snippet = str(r['clean_apply_url'])[:45] + "..."
        print(f"{r['rank']:<5} {r['match_score']:<7} {comp:<24} {plat:<15} {url_snippet}")
    print("=" * 100)

if __name__ == "__main__":
    main()
