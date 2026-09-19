"""
JobSpy-powered multi-portal job scraper.
Exposes a FastAPI endpoint POST /api/scrape/jobspy that the Java backend calls.
Also runnable standalone: python job_scraper.py
"""

import time
import json
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from jobspy import scrape_jobs
from fastapi import APIRouter

logger = logging.getLogger("job_scraper")

router = APIRouter()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SEARCH_TERMS = [
    "Java Backend Developer",
    "Java Software Engineer",
    "Java Developer",
    "Backend Engineer",
    "Software Engineer",
    "Spring Boot Developer",
    "Java Microservices",
    "SDE II",
    "SDE 2",
    "Full Stack Developer Java",
    "Backend Engineer Java",
    "Software Engineer Backend",
    "software engineer",
    "backend engineer",
    "full stack developer",
]

LOCATIONS = [
    "Delhi NCR, India",
    "Gurugram, India",
    "Noida, India",
    "Bangalore, India",
    "Hyderabad, India",
    "Pune, India",
]

SITES = ["linkedin", "indeed"]      # naukri not yet supported by jobspy
RESULTS_PER_QUERY = 15              # modest per (term, location) to avoid blocks
HOURS_OLD = 24 * 14                 # last 2 weeks
SLEEP_BETWEEN_QUERIES = 3           # seconds between queries


def run_full_scrape(
    search_terms: Optional[list[str]] = None,
    locations: Optional[list[str]] = None,
    sites: Optional[list[str]] = None,
    results_per_query: int = RESULTS_PER_QUERY,
    hours_old: int = HOURS_OLD,
    include_remote: bool = True,
) -> pd.DataFrame:
    """
    Execute the full matrix scrape and return a deduplicated DataFrame.
    """
    terms = search_terms or SEARCH_TERMS
    locs = locations or LOCATIONS
    site_list = sites or SITES

    all_jobs: list[pd.DataFrame] = []
    total_queries = 0
    failed_queries = 0

    # --- Location-based queries ---
    for term in terms:
        for location in locs:
            total_queries += 1
            logger.info(f"[JobSpy] Scraping: '{term}' in '{location}' on {site_list}...")
            try:
                jobs = scrape_jobs(
                    site_name=site_list,
                    search_term=term,
                    location=location,
                    results_wanted=results_per_query,
                    hours_old=hours_old,
                    country_indeed="India",
                    linkedin_fetch_description=True,
                )
                jobs["search_term"] = term
                jobs["search_location"] = location
                all_jobs.append(jobs)
                logger.info(f"  -> Got {len(jobs)} results")
            except Exception as e:
                failed_queries += 1
                logger.warning(f"  -> Failed: {e}")
            time.sleep(SLEEP_BETWEEN_QUERIES)

    # --- Remote queries ---
    if include_remote:
        for term in terms:
            total_queries += 1
            logger.info(f"[JobSpy] Scraping remote: '{term}' on {site_list}...")
            try:
                jobs = scrape_jobs(
                    site_name=site_list,
                    search_term=term,
                    location="India",
                    is_remote=True,
                    results_wanted=results_per_query,
                    hours_old=hours_old,
                    country_indeed="India",
                    linkedin_fetch_description=True,
                )
                jobs["search_term"] = term
                jobs["search_location"] = "Remote"
                all_jobs.append(jobs)
                logger.info(f"  -> Got {len(jobs)} remote results")
            except Exception as e:
                failed_queries += 1
                logger.warning(f"  -> Failed: {e}")
            time.sleep(SLEEP_BETWEEN_QUERIES)

    if not all_jobs:
        logger.error("[JobSpy] No jobs collected from any query!")
        return pd.DataFrame()

    # --- Combine, dedupe ---
    df = pd.concat(all_jobs, ignore_index=True)
    total_raw = len(df)

    # Drop rows with no useful description
    df = df[df["description"].notna() & (df["description"].str.len() > 50)]

    # Dedupe on job_url (same posting surfaces across multiple search-term loops)
    df = df.drop_duplicates(subset=["job_url"])
    total_deduped = len(df)
    duplicates_removed = total_raw - total_deduped

    logger.info("=" * 70)
    logger.info("📊 [JOBSPY SCRAPE SUMMARY REPORT]")
    logger.info(f"   Total Queries Executed      : {total_queries}")
    logger.info(f"   Failed Queries              : {failed_queries}")
    logger.info(f"   Total Raw Jobs Fetched      : {total_raw}")
    logger.info(f"   Duplicates Removed          : {duplicates_removed}")
    logger.info(f"   Unique Jobs with JD         : {total_deduped}")
    logger.info("=" * 70)

    return df


def dataframe_to_job_dtos(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame rows to JSON-serializable job DTOs for the Java backend."""
    jobs = []
    for _, row in df.iterrows():
        posted_at = None
        if pd.notna(row.get("date_posted")):
            try:
                posted_at = pd.Timestamp(row["date_posted"]).isoformat()
            except Exception:
                posted_at = datetime.now().isoformat()

        job = {
            "platform": str(row.get("site", "Unknown")).capitalize(),
            "externalId": f"jspy-{str(row.get('site', 'unk')).lower()}-{str(row.get('company', '')).lower().replace(' ', '')}-{str(row.get('title', '')).lower().replace(' ', '')[:40]}",
            "title": str(row.get("title", "")),
            "companyName": str(row.get("company", "")),
            "location": str(row.get("location", "")),
            "experienceMin": 2.0,
            "experienceMax": 5.0,
            "description": str(row.get("description", "")),
            "skills": ["Java", "Spring Boot", "REST APIs", "Microservices", "SQL"],
            "salaryRange": _format_salary(row),
            "jobUrl": str(row.get("job_url", "")),
            "recruiterName": str(row.get("site", "Portal")) + " Recruiter",
            "recruiterEmail": None,
            "postedAt": posted_at,
        }
        jobs.append(job)
    return jobs


def _format_salary(row) -> str:
    min_amt = row.get("min_amount")
    max_amt = row.get("max_amount")
    currency = row.get("currency", "")
    if pd.notna(min_amt) and pd.notna(max_amt):
        return f"{currency} {int(min_amt):,} - {int(max_amt):,}"
    elif pd.notna(min_amt):
        return f"{currency} {int(min_amt):,}+"
    return "Disclosed on apply"


# ---------------------------------------------------------------------------
# FastAPI endpoint
# ---------------------------------------------------------------------------

@router.post("/api/scrape/jobspy")
async def scrape_jobspy_endpoint(
    search_terms: Optional[list[str]] = None,
    locations: Optional[list[str]] = None,
    sites: Optional[list[str]] = None,
    results_per_query: int = RESULTS_PER_QUERY,
    hours_old: int = HOURS_OLD,
    include_remote: bool = True,
):
    """
    Trigger a full matrix scrape via JobSpy.
    Returns JSON list of job DTOs ready for Java backend to persist.
    """
    import asyncio
    loop = asyncio.get_event_loop()

    # Run blocking scrape in a thread pool to not block the event loop
    df = await loop.run_in_executor(
        None,
        lambda: run_full_scrape(
            search_terms=search_terms,
            locations=locations,
            sites=sites,
            results_per_query=results_per_query,
            hours_old=hours_old,
            include_remote=include_remote,
        ),
    )

    jobs = dataframe_to_job_dtos(df)

    return {
        "totalJobs": len(jobs),
        "jobs": jobs,
    }


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    df = run_full_scrape()

    print(f"\nCollected {len(df)} unique job postings with descriptions.")

    # Save to CSV
    csv_path = "swe_jobs_india.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved to {csv_path}")

    # Also save as JSON for Java backend consumption
    jobs = dataframe_to_job_dtos(df)
    json_path = "swe_jobs_india.json"
    with open(json_path, "w") as f:
        json.dump({"totalJobs": len(jobs), "jobs": jobs}, f, indent=2, default=str)
    print(f"Saved JSON to {json_path}")
