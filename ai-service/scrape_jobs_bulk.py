

import time
import pandas as pd
from jobspy import scrape_jobs

# --- Config -------------------------------------------------------------

# Trimmed from CandidateTargetCriteria.getSearchKeywords() — high-signal
# subset rather than all 14, to keep runtime reasonable (dedup handles any
# overlap between similar terms anyway).
SEARCH_TERMS = [
    "Java Backend Developer",
    "Java Software Engineer",
    "Spring Boot Developer",
    "SDE 2",
    "Backend Engineer Java",
]

LOCATIONS = [
    "Delhi NCR, India",
    "Gurugram, India",
    "Noida, India",
    "Bangalore, India",
    "Hyderabad, India",
    "Pune, India",
]

SITES = ["linkedin", "indeed", "naukri"]

RESULTS_PER_QUERY = 15   # keep modest per (term, location) combo to avoid blocks
HOURS_OLD = 24 * 14      # last 2 weeks of postings

# Target experience band, from CandidateTargetCriteria (min/max experience)
MIN_EXPERIENCE = 2.0
MAX_EXPERIENCE = 5.0

# --- Scrape ---------------------------------------------------------------

all_jobs = []

for term in SEARCH_TERMS:
    for location in LOCATIONS:
        print(f"Scraping: '{term}' in '{location}'...")
        try:
            jobs = scrape_jobs(
                site_name=SITES,
                search_term=term,
                location=location,
                results_wanted=RESULTS_PER_QUERY,
                hours_old=HOURS_OLD,
                country_indeed="India",
                linkedin_fetch_description=True,  # pulls full JD text
                # proxies=["http://user:pass@host:port"],  # uncomment if blocked
            )
            jobs["search_term"] = term
            jobs["search_location"] = location
            all_jobs.append(jobs)
            print(f"  -> fetched {len(jobs)} jobs for '{term}' in '{location}'")
        except Exception as e:
            print(f"  failed: {e}")
        time.sleep(5)  # be polite between queries

# Also grab a batch of pure-remote roles (India-eligible)
for term in SEARCH_TERMS:
    print(f"Scraping remote: '{term}'...")
    try:
        jobs = scrape_jobs(
            site_name=SITES,
            search_term=term,
            location="India",
            is_remote=True,
            results_wanted=RESULTS_PER_QUERY,
            hours_old=HOURS_OLD,
            country_indeed="India",
            linkedin_fetch_description=True,
        )
        jobs["search_term"] = term
        jobs["search_location"] = "Remote"
        all_jobs.append(jobs)
        print(f"  -> fetched {len(jobs)} remote jobs for '{term}'")
    except Exception as e:
        print(f"  failed: {e}")
    time.sleep(5)

# --- Combine, dedupe, save --------------------------------------------------

if not all_jobs:
    print("No jobs were collected.")
else:
    df = pd.concat(all_jobs, ignore_index=True)

    # Drop rows with no description at all (not useful for JD analysis)
    df = df[df["description"].notna() & (df["description"].str.len() > 50)]

    # Dedupe on job_url (same posting can surface across search-term loops)
    df = df.drop_duplicates(subset=["job_url"])

    print(f"\nCollected {len(df)} job postings with descriptions "
          f"(pre-experience-filter).")

    df.to_csv("swe_jobs_india_all.csv", index=False)
    print("Saved full set to swe_jobs_india_all.csv")

    # --- Optional experience-band filter (Naukri only has structured data) --
    # Naukri gives a structured `experience_range` field. LinkedIn/Indeed
    # don't expose one via JobSpy, so for those we do a loose text scan of
    # title+description for a YOE mention instead — not exact, but filters
    # out obviously mismatched postings (fresher-only, 8+ yrs senior, etc).
    def matches_experience(row):
        if row.get("site") == "naukri" and pd.notna(row.get("experience_range")):
            # crude parse of strings like "2-5 Yrs" or "2-4 Yrs"
            import re
            nums = re.findall(r"\d+", str(row["experience_range"]))
            if len(nums) >= 2:
                lo, hi = int(nums[0]), int(nums[1])
                return lo <= MAX_EXPERIENCE and hi >= MIN_EXPERIENCE
            return True  # can't parse — keep it, don't discard silently
        # No structured data for other sites — keep everything;
        # eyeball these manually when reviewing the CSV.
        return True

    df["likely_experience_match"] = df.apply(matches_experience, axis=1)

    print(f"Of these, {df['likely_experience_match'].sum()} look like a "
          f"{MIN_EXPERIENCE}-{MAX_EXPERIENCE} yr match (Naukri-verified; "
          f"others unverified — review manually).")

    # Trim to ~100 if you pulled more than needed, preferring matches first
    df_sorted = df.sort_values("likely_experience_match", ascending=False)
    if len(df_sorted) > 100:
        df_sorted.head(100).to_csv("swe_jobs_india_sample100.csv", index=False)
        print("Also saved a 100-row sample: swe_jobs_india_sample100.csv")

