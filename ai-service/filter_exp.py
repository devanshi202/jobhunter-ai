"""
Experience-range extractor — post-processes your already-scraped JD CSV
(swe_jobs_india_all.csv) to determine each posting's required experience
band from raw text, since LinkedIn/Indeed don't give structured experience
data like Naukri does.

Scans title + description for common phrasings:
    "2-5 years", "2 to 5 years", "3+ years", "minimum 4 years",
    "at least 2 years of experience", etc.

Produces a tri-state `experience_match` column:
    True    - extracted range overlaps your target band
    False   - extracted range does NOT overlap (e.g. "5-10 years", "0-1 years")
    None    - couldn't confidently extract a range from the text (review manually)

This is heuristic text-matching, not perfect — JDs sometimes mention multiple
year figures for unrelated reasons (e.g. "5+ years in the industry" for the
company, not the role). Treat `False` as "probably skip," and `None` as
"worth a quick manual read," rather than fully trusting either blindly.

Usage:
    python filter_experience.py
"""

import re
import pandas as pd

# --- Config -------------------------------------------------------------

INPUT_CSV = "swe_jobs_india_all.csv"
OUTPUT_CSV = "swe_jobs_india_all_with_experience.csv"

MIN_EXPERIENCE = 2.0
MAX_EXPERIENCE = 5.0

# --- Extraction logic -----------------------------------------------------

def extract_experience_range(text: str):
    """Returns (lo, hi) years, or (None, None) if nothing confidently found.
    hi=None with a valid lo means an open-ended '3+ years' style requirement."""
    text = text.lower()

    # "2-5 years" / "2 to 5 years" / "2 - 5 yrs"
    range_matches = re.findall(r"(\d+)\s*(?:-|to)\s*(\d+)\s*\+?\s*years?", text)
    range_matches += re.findall(r"(\d+)\s*(?:-|to)\s*(\d+)\s*\+?\s*yrs?", text)

    # "3+ years" / "3+ yrs"
    plus_matches = re.findall(r"(\d+)\s*\+\s*(?:years?|yrs?)", text)

    # "minimum 4 years" / "at least 2 years of experience"
    min_kw_matches = re.findall(
        r"(?:minimum|at least)(?:\s*of)?\s*(\d+)\s*(?:years?|yrs?)", text
    )

    mins, maxs = [], []
    for lo, hi in range_matches:
        mins.append(int(lo))
        maxs.append(int(hi))
    for n in plus_matches:
        mins.append(int(n))
    for n in min_kw_matches:
        mins.append(int(n))

    if not mins and not maxs:
        return None, None

    lo = min(mins) if mins else None
    hi = max(maxs) if maxs else None
    return lo, hi


def matches_target(lo, hi, min_target, max_target):
    if lo is None and hi is None:
        return None  # couldn't extract anything
    if lo is None:
        lo = 0
    if hi is None:
        hi = 99  # open-ended "n+ years" — treat as no upper cap
    # Overlap check between [lo, hi] and [min_target, max_target]
    return lo <= max_target and hi >= min_target


# --- Apply to CSV -----------------------------------------------------------

df = pd.read_csv(INPUT_CSV)

def process_row(row):
    text = f"{row.get('title', '')} {row.get('description', '')}"
    lo, hi = extract_experience_range(str(text))
    match = matches_target(lo, hi, MIN_EXPERIENCE, MAX_EXPERIENCE)
    return pd.Series({"extracted_min_yoe": lo, "extracted_max_yoe": hi, "experience_match": match})

extracted = df.apply(process_row, axis=1)
df = pd.concat([df, extracted], axis=1)

df.to_csv(OUTPUT_CSV, index=False)

print(f"Total rows: {len(df)}")
print(f"  Matches target ({MIN_EXPERIENCE}-{MAX_EXPERIENCE} yrs):  {(df['experience_match'] == True).sum()}")
print(f"  Does NOT match:                     {(df['experience_match'] == False).sum()}")
print(f"  Unclear (couldn't extract, review):  {df['experience_match'].isna().sum()}")
print(f"\nSaved to {OUTPUT_CSV}")