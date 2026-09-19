"""
01_scrape_jobs.py — Bulk Job Scraper (JobSpy)

Scrapes LinkedIn and Indeed using search parameters defined in config.py.
Saves deduplicated jobs with full descriptions to output/swe_jobs_scraped.csv.
"""

import time
import pandas as pd
from jobspy import scrape_jobs
import config

def run_scraper():
    print("=" * 70)
    print("🚀 STEP 1: BULK JOB SCRAPING (JobSpy)")
    print("=" * 70)
    print(f"Target sites: {config.SITES}")
    print(f"Search terms: {config.SEARCH_TERMS}")
    print(f"Locations   : {config.LOCATIONS}")
    print(f"Results/term: {config.RESULTS_PER_QUERY} | Hours old: {config.HOURS_OLD}")
    print("-" * 70)

    all_jobs = []

    # 1. Location-based search
    for term in config.SEARCH_TERMS:
        for location in config.LOCATIONS:
            print(f"Scraping: '{term}' in '{location}'...")
            try:
                jobs = scrape_jobs(
                    site_name=config.SITES,
                    search_term=term,
                    location=location,
                    results_wanted=config.RESULTS_PER_QUERY,
                    hours_old=config.HOURS_OLD,
                    country_indeed="India",
                    linkedin_fetch_description=True,
                )
                if not jobs.empty:
                    jobs["search_term"] = term
                    jobs["search_location"] = location
                    all_jobs.append(jobs)
                    print(f"  -> fetched {len(jobs)} jobs for '{term}' in '{location}'")
            except Exception as e:
                print(f"  failed: {e}")
            time.sleep(4)

    # 2. Remote search
    for term in config.SEARCH_TERMS:
        print(f"Scraping remote: '{term}'...")
        try:
            jobs = scrape_jobs(
                site_name=config.SITES,
                search_term=term,
                location="India",
                is_remote=True,
                results_wanted=config.RESULTS_PER_QUERY,
                hours_old=config.HOURS_OLD,
                country_indeed="India",
                linkedin_fetch_description=True,
            )
            if not jobs.empty:
                jobs["search_term"] = term
                jobs["search_location"] = "Remote"
                all_jobs.append(jobs)
                print(f"  -> fetched {len(jobs)} remote jobs for '{term}'")
        except Exception as e:
            print(f"  failed: {e}")
        time.sleep(4)

    # 3. Combine, dedupe & save
    if not all_jobs:
        print("❌ No jobs were collected.")
        return

    df = pd.concat(all_jobs, ignore_index=True)
    df = df[df["description"].notna() & (df["description"].str.len() > 50)]
    df = df.drop_duplicates(subset=["job_url"])

    print(f"\n✅ Collected {len(df)} unique jobs with full descriptions.")
    df.to_csv(config.SCRAPED_JOBS_CSV, index=False)
    print(f"📁 Saved to: {config.SCRAPED_JOBS_CSV}")
    print("=" * 70)

if __name__ == "__main__":
    run_scraper()
