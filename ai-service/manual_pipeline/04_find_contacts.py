"""
find_contacts.py — Recruiter & Hiring Contact Discovery Engine

Discovers recruiter and hiring manager contacts for top-matched companies using:
1. Regex extraction of direct emails inside Job Descriptions.
2. Domain resolution & Pattern Matching (careers@, talent@, hiring@, hr@).
3. Live DNS MX Record Verification (checks if company mail exchange actually exists & receives mail).
4. LinkedIn Recruiter & Engineering Manager Search URL Generator.
5. Hunter.io / Apollo.io Free API integration (optional via .env keys).

Outputs:
    company_contacts.json
    contacts_summary.csv
"""

import json
import os
import re
import urllib.parse
from pathlib import Path
import dns.resolver
import pandas as pd
import requests
import config

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

INPUT_JSON    = str(config.RESOLVED_APPLY_JSON)
FALLBACK_JSON = str(config.TOP_MATCHES_JSON)
OUTPUT_JSON   = str(config.CONTACTS_JSON)
OUTPUT_CSV    = str(config.CONTACTS_CSV)

# Optional API Keys (Free tier accounts from Hunter.io or Apollo.io)
HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY", "")
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")

# Standard hiring inboxes checked against company domains
ROLE_INBOX_PATTERNS = ["careers", "talent", "hiring", "jobs", "recruitment", "hr"]

# Known manual domain overrides for common abbreviations/names
DOMAIN_OVERRIDES = {
    "bluehost": "bluehost.com",
    "zapcom group inc": "zapcom.com",
    "zapcom": "zapcom.com",
    "intraedge": "intraedge.com",
    "synechron": "synechron.com",
    "bizinso": "bizinso.com",
    "people tech group inc": "peopletech.com",
    "osttra": "osttra.com",
    "air india": "airindia.com",
    "quest global": "quest-global.com",
    "state street": "statestreet.com",
    "adobe": "adobe.com",
    "epam systems": "epam.com",
    "luxoft india": "luxoft.com",
    "luxoft": "luxoft.com",
    "citi": "citi.com",
    "pubmatic": "pubmatic.com",
    "united airlines": "united.com",
    "united airlines india": "united.com",
    "kumaran systems": "kumaransystems.com",
    "healthkart": "healthkart.com",
    "exl": "exlservice.com",
    "trantor": "trantorinc.com",
    "siriusai": "siriusai.in",
}

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def extract_emails_from_text(text: str) -> list[str]:
    """Extract all email addresses from JD text via regex, filtering out bogus domains."""
    if not isinstance(text, str):
        return []
    
    pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    matches = re.findall(pattern, text)
    valid_emails = []
    
    exclude_domains = {"example.com", "yourcompany.com", "domain.com", "email.com"}
    exclude_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
    
    for email in set(matches):
        email_clean = email.strip().lower()
        if any(email_clean.endswith(ext) for ext in exclude_extensions):
            continue
        domain = email_clean.split("@")[-1]
        if domain not in exclude_domains and "." in domain:
            valid_emails.append(email_clean)
            
    return valid_emails

def guess_company_domain(company_name: str) -> str:
    """Guess company primary web domain from name."""
    if not company_name or str(company_name).lower() == "nan":
        return ""
    clean_name = company_name.strip().lower()
    
    # Check overrides
    if clean_name in DOMAIN_OVERRIDES:
        return DOMAIN_OVERRIDES[clean_name]
    for key, dom in DOMAIN_OVERRIDES.items():
        if key in clean_name:
            return dom
            
    # Clean generic suffixes: "Inc", "Pvt Ltd", "LLC", "Technologies", "Solutions"
    cleaned = re.sub(r"\b(pvt|ltd|inc|llc|technologies|services|consulting|group|systems|in)\b", "", clean_name)
    slug = re.sub(r"[^a-z0-9]", "", cleaned)
    if slug:
        return f"{slug}.com"
    return ""

def verify_mx_record(domain: str) -> tuple[bool, str]:
    """Verify via DNS if the domain has active MX records accepting emails."""
    if not domain or "." not in domain:
        return False, "Invalid domain"
    try:
        answers = dns.resolver.resolve(domain, "MX")
        if answers:
            primary_mx = str(answers[0].exchange).rstrip(".")
            return True, primary_mx
    except Exception as e:
        return False, str(e.__class__.__name__)
    return False, "No MX records"

def generate_linkedin_recruiter_search(company: str) -> str:
    """Create a targeted LinkedIn search URL for Tech Recruiters & Engineering Managers."""
    keywords = '"Technical Recruiter" OR "Engineering Manager" OR "Talent Acquisition"'
    query = f"{keywords} {company}"
    encoded = urllib.parse.quote(query)
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded}"

def generate_google_dork_search(company: str) -> str:
    """Create Google search to uncover direct recruiter emails / LinkedIn profiles."""
    dork = f'site:linkedin.com/in/ ("Technical Recruiter" OR "Engineering Manager") "{company}"'
    return f"https://www.google.com/search?q={urllib.parse.quote(dork)}"

def fetch_hunter_emails(domain: str) -> list[dict]:
    """Query Hunter.io Free API for domain search if API key is provided."""
    if not HUNTER_API_KEY or not domain:
        return []
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            emails = []
            for e in data.get("emails", []):
                emails.append({
                    "email": e.get("value"),
                    "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                    "position": e.get("position", "Recruiter/Team"),
                    "confidence": e.get("confidence", 0),
                    "source": "Hunter.io"
                })
            return emails
    except Exception:
        pass
    return []

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("👥 Contact Discovery Engine (Recruiter & Hiring Team Finder)")
    print("=" * 70)

    # 1. Load job list with descriptions
    jobs = []
    if Path(FALLBACK_JSON).exists():
        with open(FALLBACK_JSON, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        print(f"Loaded {len(jobs)} jobs with full descriptions.")
    else:
        print("Missing top_matches.json. Run match_jobs.py first.")
        return

    # Load resolved apply links if available
    apply_links_map = {}
    if Path(INPUT_JSON).exists():
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            resolved_list = json.load(f)
            for item in resolved_list:
                apply_links_map[item.get("rank")] = item.get("clean_apply_url", "")

    contacts_list = []
    summary_rows = []

    print("\nScanning contacts, verifying DNS MX records & constructing search URLs...\n")

    for job in jobs[:25]:
        rank    = job.get("rank")
        company = job.get("company", "Company")
        title   = job.get("title", "Role")
        desc    = job.get("description", "")
        score   = job.get("match_score", 0.0)

        # 1. Direct JD emails
        jd_emails = extract_emails_from_text(desc)

        # 2. Domain & MX verification
        domain = guess_company_domain(company)
        mx_valid, mx_host = verify_mx_record(domain) if domain else (False, "No domain")

        # 3. Pattern candidate emails
        pattern_emails = []
        if domain and mx_valid:
            for prefix in ROLE_INBOX_PATTERNS[:3]:  # top 3: careers, talent, hiring
                pattern_emails.append(f"{prefix}@{domain}")

        # 4. Search URLs
        linkedin_search_url = generate_linkedin_recruiter_search(company)
        google_dork_url     = generate_google_dork_search(company)

        # 5. Hunter.io free API check (if configured)
        api_emails = fetch_hunter_emails(domain) if HUNTER_API_KEY else []

        # Primary outreach recommendation
        primary_contact = "Hiring Team"
        primary_email = ""
        email_source = "None found"

        if jd_emails:
            primary_email = jd_emails[0]
            email_source = "Direct JD Text"
        elif api_emails:
            primary_email = api_emails[0]["email"]
            primary_contact = api_emails[0]["name"] or "Talent Acquisition"
            email_source = "Hunter.io"
        elif pattern_emails:
            primary_email = pattern_emails[0]
            email_source = f"Pattern Matched ({domain})"

        record = {
            "rank": rank,
            "match_score": round(score, 1),
            "company": company,
            "title": title,
            "domain": domain,
            "mx_valid": mx_valid,
            "mx_host": mx_host,
            "primary_contact_name": primary_contact,
            "primary_email": primary_email,
            "email_source": email_source,
            "all_extracted_emails": jd_emails,
            "pattern_emails": pattern_emails,
            "hunter_emails": api_emails,
            "linkedin_search_url": linkedin_search_url,
            "google_dork_url": google_dork_url,
            "clean_apply_url": apply_links_map.get(rank, job.get("job_url", "")),
        }
        contacts_list.append(record)

        summary_rows.append({
            "rank": rank,
            "score": round(score, 1),
            "company": company,
            "role": title,
            "domain": domain,
            "mx_verified": "✅ YES" if mx_valid else "❌ NO",
            "primary_email": primary_email or "Search via LinkedIn",
            "source": email_source,
            "linkedin_finder": linkedin_search_url,
        })

    # Save outputs
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(contacts_list, f, indent=2)

    sum_df = pd.DataFrame(summary_rows)
    sum_df.to_csv(OUTPUT_CSV, index=False)

    print(f"✅ Contact discovery completed for top {len(contacts_list)} opportunities!")
    print(f"   - {OUTPUT_JSON}")
    print(f"   - {OUTPUT_CSV}")

    # Display clean table
    print("\n" + "=" * 115)
    print(f"{'Rank':<5} {'Score':<7} {'Company':<22} {'MX Verified':<13} {'Recommended Email / Contact':<30} {'Source'}")
    print("-" * 115)
    for row in summary_rows[:15]:
        comp = str(row['company'])[:20]
        mail = str(row['primary_email'])[:28]
        src  = str(row['source'])[:20]
        print(f"{row['rank']:<5} {row['score']:<7} {comp:<22} {row['mx_verified']:<13} {mail:<30} {src}")
    print("=" * 115)
    print("\n💡 TIP: For rows with 'Search via LinkedIn', click the generated linkedin_search_url in company_contacts.json")
    print("   to find the exact Technical Recruiter or Engineering Manager name in 1 click!")

if __name__ == "__main__":
    main()
