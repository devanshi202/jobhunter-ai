"""
match_jobs_v3.py — Semantic + Weighted Skill + Experience + Domain + Location
Job Matcher (v3)

Compares the candidate's resume against all scraped job descriptions and
produces a ranked CSV of best-fit opportunities.

Algorithm (5-component weighted score):
  1. Semantic Similarity   (40%) — cosine similarity of sentence-transformer
                                   embeddings (title + description on the JD
                                   side), min-max normalized within this run.
  2. Skill Overlap         (25%) — WEIGHTED Jaccard similarity between the
                                   candidate skill set and skills extracted
                                   from JD title + description. Core skills
                                   (Java, Spring Boot, SQL, ...) count more
                                   than supporting tools (Ollama, pgvector, ...)
                                   in both the overlap and the union.
  3. Experience Fit        (15%) — smooth (not stepped) proximity of candidate
                                   YOE to any detected experience requirement,
                                   scoped to a requirements/qualifications
                                   section when one can be found.
  4. Domain Fit            (10%) — NEW. Credit for Capital Markets / BFSI /
                                   fintech signal in the JD, matching the
                                   candidate's actual domain background.
  5. Location Fit          (10%) — NEW. Credit for Delhi-NCR postings or
                                   remote roles, since a perfect skill match
                                   in an unreachable city is not equally
                                   actionable.

CHANGES FROM v2:
  - Fix #6: skill matching is now a WEIGHTED Jaccard, not a flat one. Every
    skill in SKILL_VOCAB carries a tier weight (CORE / IMPORTANT /
    SUPPORTING). Previously "Java" and "Ollama" contributed identically to
    skill_score, which both overstated marginal-tool matches and understated
    strong core-stack matches.
  - Fix #7: skill extraction (both sides) and the semantic embedding now
    include the JOB TITLE, not just the description. Several JDs state their
    core stack ("Java, Spring, REST API, Microservices") only in the title
    and use generic language in the body — v2 silently scored these low.
  - Fix #8: experience_fit_score is now a smooth linear decay based on the
    actual year-gap instead of hard-coded buckets (0.75 / 0.50 / 0.20), so
    two JDs asking for "3-5" and "3-6" years no longer land on arbitrarily
    different sides of a cliff.
  - Fix #9: added domain_fit_score — explicit credit for Capital Markets /
    BFSI / fintech / insurance signal, which neither v1 nor v2 scored at all
    despite it being a real, resume-stated differentiator.
  - Fix #10: added location_fit_score — credit for Delhi-NCR postings and
    remote roles.
  - Fix #11: added dedupe_jobs() — v2's output could contain the same
    posting more than once (same title + company scraped from multiple
    boards), diluting the top-N shortlist. Duplicates are now collapsed,
    keeping the most complete (longest-description) copy.
  - Weights rebalanced to make room for the two new components:
        v2: semantic .50 / skill .30 / exp .20
        v3: semantic .40 / skill .25 / exp .15 / domain .10 / location .10
    All five are declared in one WEIGHTS dict so they're easy to re-tune,
    and main() asserts they sum to 1.0 so a typo can't silently skew scoring.
  - Carried over unchanged from v2 (still correct): candidate skills derived
    from CANDIDATE_RESUME_TEXT via the same vocabulary used for JDs (v2
    Fix #2), requirements-section scoping for experience extraction (v2
    Fix #3), and the min-max semantic normalization (v2 Fix #1).

Usage:
    cd ai-service
    source venv/bin/activate
    python match_jobs_v3.py

Outputs:
    matched_jobs_ranked_v3.csv   — all jobs, deduped, sorted by match_score
    top_matches_v3.json          — top 25 jobs, with full detail for email writer
"""

import re
import json
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

JD_CSV          = "swe_jobs_india_all.csv"   # update to match your actual current file
OUTPUT_CSV      = "matched_jobs_ranked_v3.csv"
OUTPUT_JSON     = "top_matches_v3.json"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"         # fast, high-quality bi-encoder
TOP_N           = 25                          # rows saved to top_matches.json

# Candidate profile (Devanshi Sharma)
CANDIDATE_YOE = 2.5   # years of experience

# Component weights — must sum to 1.0 (checked at startup in main()).
WEIGHTS = {
    "semantic": 0.40,
    "skill":    0.25,
    "exp":      0.15,
    "domain":   0.10,
    "location": 0.10,
}

# Experience-gap decay: score = max(EXP_FLOOR, 1 - gap / EXP_DECAY_YEARS)
EXP_FLOOR = 0.15
EXP_DECAY_YEARS = 5.0

# ---------------------------------------------------------------------------
# SKILL VOCABULARY — tiered so overlap quality matters, not just overlap count
# ---------------------------------------------------------------------------
# CORE: the non-negotiable backend stack the candidate's target roles require.
# IMPORTANT: commonly-required secondary tooling / practices.
# SUPPORTING: nice-to-have tools, or skills only relevant to the candidate's
#             personal AI project rather than the target Java-backend role.

CORE_SKILLS = [
    "Java", "Spring Boot", "Spring Security", "Microservices",
    "REST API", "REST APIs", "RESTful", "Hibernate", "JPA",
    "SQL", "PostgreSQL", "MySQL", "Agile",
]

IMPORTANT_SKILLS = [
    "Spring MVC", "Spring Cloud", "JDBC", "AWS", "Azure", "Docker", "Jenkins",
    "CI/CD", "Git", "Maven", "Gradle", "Debugging", "Root Cause Analysis",
    "Performance Optimization", "Postman", "API Testing", "SOLID",
    "Design Patterns", "Data Structures", "Algorithms", "Scrum",
]

SUPPORTING_SKILLS = [
    "MongoDB", "Redis", "NoSQL", "Elasticsearch", "Kafka", "RabbitMQ", "gRPC",
    "GraphQL", "WebSocket", "Python", "JavaScript", "Node.js", "React",
    "Angular", "GCP", "Kubernetes", "Lambda", "EC2", "S3", "RDS", "Jira",
    "TDD", "JUnit", "Mockito", "Multithreading", "System Design",
    "Code Review", "Terraform", "GitHub Actions", "Log Analysis",
    "pgvector", "Apache Tika", "Ollama",
]

SKILL_VOCAB = CORE_SKILLS + IMPORTANT_SKILLS + SUPPORTING_SKILLS
SKILL_VOCAB_LOWER = {s.lower(): s for s in SKILL_VOCAB}

SKILL_WEIGHTS = {}
for s in CORE_SKILLS:
    SKILL_WEIGHTS[s.lower()] = 3.0
for s in IMPORTANT_SKILLS:
    SKILL_WEIGHTS[s.lower()] = 2.0
for s in SUPPORTING_SKILLS:
    SKILL_WEIGHTS[s.lower()] = 1.0

# ---------------------------------------------------------------------------
# DOMAIN / LOCATION SIGNAL
# ---------------------------------------------------------------------------

DOMAIN_TERMS = [
    "capital markets", "banking", "bfsi", "fintech", "financial services",
    "insurance", "asset management", "trading platform", "payments",
]
DOMAIN_HIT_SCORE = 1.0
DOMAIN_MISS_SCORE = 0.45  # not zero — most SWE roles are still viable outside FS

# City-level = strong location fit. State-code-level (as scraped, e.g. "HR, IN")
# is a weaker but still positive signal since it may resolve to an NCR city.
NCR_CITY_TERMS = [
    "gurugram", "gurgaon", "delhi", "noida", "greater noida", "faridabad", "ncr",
]
NCR_STATE_CODES = ["hr, in", "dl, in", "up, in"]
LOCATION_CITY_SCORE = 1.0
LOCATION_STATE_SCORE = 0.85
LOCATION_REMOTE_SCORE = 0.75
LOCATION_OTHER_SCORE = 0.35

# ---------------------------------------------------------------------------
# CANDIDATE RESUME TEXT (used for embedding AND skill extraction)
# ---------------------------------------------------------------------------
# Keep this block in sync with the actual resume file whenever it's updated —
# every score in this script's output is only as current as this text.

CANDIDATE_RESUME_TEXT = """
Software Engineer with 2.5+ years of experience developing and maintaining
enterprise Java backend applications in the Capital Markets domain. Skilled in
Java, Spring Boot, Microservices, SQL, REST APIs, debugging, root cause
analysis, performance optimization, and production releases in Agile
environments. Experienced with AWS, Azure, Docker, Jenkins, PostgreSQL, MySQL,
and backend engineering practices including SOLID principles and design
patterns. Currently building an AI-powered Job Search Automation platform using
Spring Boot, Python, PostgreSQL, pgvector, Docker, and Ollama. Seeking Java
Backend / Software Engineer opportunities focused on scalable backend and
distributed systems.

Experience:
- Developed and maintained enterprise Java-based backend applications for a
  Capital Markets platform (TCS BaNCS) for Société Générale.
- Investigated and resolved 80+ UAT and production-impacting application issues
  through Java debugging, SQL-based data analysis, and root cause analysis.
- Implemented 20+ client-driven change requests and backend product enhancements
  across multiple Agile release cycles.
- Supported 10+ UAT and production release cycles, API validation with Postman,
  and contributed to application stability.
- Built backend applications using Java, Spring Boot, Hibernate, Spring Security,
  REST APIs; cloud solutions on AWS and Azure; CI/CD with Jenkins.
- Developed backend features for catalogue management at Blinkit.
- Built AI-powered Job Search Automation using Spring Boot, Python, PostgreSQL,
  pgvector, Ollama; implemented semantic job matching with vector embeddings.
  Reduced personal daily job-screening effort from ~40 minutes to under 2
  minutes and cut ~6.5 hours of manual JD review over a 2-week test period,
  while increasing job discovery volume 40x.
- Built full-stack product review platform with Spring Boot, Angular, JWT,
  Spring Security, Hibernate, MySQL.

Skills:
Java, Spring Boot, Microservices, REST APIs, Spring Security, Hibernate, JPA,
SQL, PostgreSQL, MySQL, MongoDB, AWS, Azure, Docker, Jenkins, CI/CD, Git,
Maven, Agile, Scrum, SOLID, Design Patterns, Python, JavaScript, Postman,
Apache Tika, Ollama, pgvector.
"""

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def build_match_text(title: str, description: str) -> str:
    """
    Fix #7: concatenate title + description so skill extraction and the
    semantic embedding both see stack keywords that appear only in the title
    (common for terse or template-generated JDs).
    """
    title = title if isinstance(title, str) else ""
    description = description if isinstance(description, str) else ""
    return f"{title}. {description}".strip(". ").strip()


def extract_skills_from_text(text: str) -> set:
    """Extract skill tokens from text using word-boundary matching."""
    if not isinstance(text, str) or not text.strip():
        return set()
    found = set()
    for skill_lower, skill_orig in SKILL_VOCAB_LOWER.items():
        pattern = r"\b" + re.escape(skill_lower) + r"\b"
        if re.search(pattern, text.lower()):
            found.add(skill_lower)
    return found


def weighted_jaccard_skill_score(candidate_skills: set, jd_skills: set) -> float:
    """
    Fix #6: weighted Jaccard similarity between two skill sets, so a shared
    core skill (Java, SQL, Spring Boot) counts for more than a shared
    supporting tool (Ollama, pgvector) in both the overlap and the union.
    Falls back gracefully to an unweighted Jaccard behaviour when both sets
    are empty.
    """
    if not jd_skills:
        return 0.0
    overlap = candidate_skills & jd_skills
    union = candidate_skills | jd_skills
    if not union:
        return 0.0
    overlap_w = sum(SKILL_WEIGHTS.get(s, 1.0) for s in overlap)
    union_w = sum(SKILL_WEIGHTS.get(s, 1.0) for s in union)
    return overlap_w / union_w if union_w else 0.0


def get_requirements_section(text: str) -> str:
    """
    Scope experience extraction to a requirements/qualifications section when
    one exists, to avoid false hits from company-history sentences like
    '20 years of experience in fintech' (about the company, not the role).
    Falls back to the whole text if no marker is found. (Unchanged from v2.)
    """
    if not isinstance(text, str):
        return ""
    markers = [
        "requirements", "qualifications", "must have", "who you are",
        "what you'll need", "what we're looking for", "skills required",
        "eligibility",
    ]
    text_lower = text.lower()
    for marker in markers:
        idx = text_lower.find(marker)
        if idx != -1:
            return text[idx:]
    return text


def extract_yoe_from_text(text: str) -> tuple:
    """
    Extract (min_yoe, max_yoe) from JD text using common patterns.
    Returns (None, None) if not found. (Unchanged from v2.)
    """
    if not isinstance(text, str):
        return None, None

    text_lower = text.lower()

    patterns = [
        r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:years?|yrs?)",
        r"(\d+)\s*\+\s*(?:years?|yrs?)",
        r"minimum\s+(\d+)\s*(?:years?|yrs?)",
        r"at\s+least\s+(\d+)\s*(?:years?|yrs?)",
        r"(\d+)\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                lo, hi = float(groups[0]), float(groups[1])
            else:
                lo = float(groups[0])
                hi = lo + 2  # assume +2 range for "X+" / bare-minimum patterns
            return lo, hi

    return None, None


def experience_fit_score(candidate_yoe: float, jd_text: str, job_level: str = "") -> float:
    """
    Fix #8: smooth linear decay based on the actual year-gap, instead of v2's
    hard-coded buckets (0.75 / 0.50 / 0.20). Two JDs asking for "3-5" and
    "3-6" years now score continuously close to each other rather than
    landing on arbitrary sides of a cliff.
      - Perfect fit (within range)          -> 1.0
      - Outside range                       -> max(EXP_FLOOR, 1 - gap / EXP_DECAY_YEARS)
      - Clearly senior/lead (lo > 7 yrs)     -> 0.1 hard floor
      - No info from JD -- job_level heuristic (unchanged, still categorical
        since job_level itself is a category, not a number)
    """
    requirements_text = get_requirements_section(jd_text)
    lo, hi = extract_yoe_from_text(requirements_text)

    # If nothing found in the scoped section, fall back to whole-text search
    if lo is None and requirements_text != jd_text:
        lo, hi = extract_yoe_from_text(jd_text)

    if lo is not None and hi is not None:
        if lo > 7:  # role clearly wants senior/lead
            return 0.1
        if lo <= candidate_yoe <= hi:
            return 1.0
        gap = min(abs(candidate_yoe - lo), abs(candidate_yoe - hi))
        return round(max(EXP_FLOOR, 1 - gap / EXP_DECAY_YEARS), 3)

    # Fall back to job_level label from LinkedIn
    if isinstance(job_level, str):
        lvl = job_level.lower()
        if "mid" in lvl or "associate" in lvl or "not applicable" in lvl:
            return 0.80
        if "entry" in lvl or "intern" in lvl:
            return 0.55
        if "director" in lvl or "executive" in lvl or "principal" in lvl:
            return 0.20
        if "senior" in lvl:
            return 0.65

    return 0.65  # neutral default


def domain_fit_score(match_text: str, company_industry: str = "") -> float:
    """
    Fix #9: credit for Capital Markets / BFSI / fintech / insurance signal in
    the JD or company industry field — a real, resume-stated differentiator
    that v1 and v2 never scored at all.
    """
    text = f"{match_text} {company_industry or ''}".lower()
    return DOMAIN_HIT_SCORE if any(term in text for term in DOMAIN_TERMS) else DOMAIN_MISS_SCORE


def location_fit_score(location: str, is_remote) -> float:
    """
    Fix #10: credit for Delhi-NCR postings or remote roles. A perfect skill
    match in a city the candidate won't relocate to isn't equally actionable
    as one in-region, but it also shouldn't be scored as if it failed the
    role fit entirely — hence graded tiers rather than a binary.
    """
    remote_flag = str(is_remote).strip().lower() in ("true", "1", "yes")
    if remote_flag:
        return LOCATION_REMOTE_SCORE
    loc = location.lower() if isinstance(location, str) else ""
    if any(term in loc for term in NCR_CITY_TERMS):
        return LOCATION_CITY_SCORE
    if any(term in loc for term in NCR_STATE_CODES):
        return LOCATION_STATE_SCORE
    return LOCATION_OTHER_SCORE


def compute_final_score(semantic: float, skill: float, exp: float,
                         domain: float, location: float) -> float:
    """Weighted combination across all five components -> 0-100 score."""
    total = (
        semantic * WEIGHTS["semantic"]
        + skill * WEIGHTS["skill"]
        + exp * WEIGHTS["exp"]
        + domain * WEIGHTS["domain"]
        + location * WEIGHTS["location"]
    )
    return round(total * 100, 2)


def score_label(score: float) -> str:
    if score >= 75: return "Excellent"
    if score >= 60: return "Strong"
    if score >= 45: return "Good"
    if score >= 30: return "Fair"
    return "Weak"


def dedupe_jobs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fix #11: v2's output could list the same posting more than once (same
    role scraped from multiple boards, or reposted under an identical
    title+company). Collapse those to a single row, keeping whichever copy
    has the longest description (most complete text to score against).
    """
    before = len(df)
    df = df.copy()
    df["_title_norm"] = df["title"].fillna("").str.strip().str.lower()
    df["_company_norm"] = df["company"].fillna("").str.strip().str.lower()
    df["_desc_len"] = df["description"].fillna("").str.len()
    df = (
        df.sort_values("_desc_len", ascending=False)
        .drop_duplicates(subset=["_title_norm", "_company_norm"], keep="first")
        .drop(columns=["_title_norm", "_company_norm", "_desc_len"])
        .reset_index(drop=True)
    )
    removed = before - len(df)
    print(f"      Deduped {removed} repeat postings (same title + company) "
          f"-> {len(df)} unique jobs remain.")
    return df


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, \
        f"WEIGHTS must sum to 1.0, got {sum(WEIGHTS.values())}"

    print("=" * 70)
    print("Job Matcher v3 -- Semantic + Weighted Skill + Experience + "
          "Domain + Location")
    print("=" * 70)

    # -- 1. Load JDs -----------------------------------------------------------
    print(f"\n[1/7] Loading job data from {JD_CSV} ...")
    df = pd.read_csv(JD_CSV)
    df = df[df["description"].notna() & (df["description"].str.len() > 50)].copy()
    df = df.reset_index(drop=True)
    print(f"      Loaded {len(df)} jobs with valid descriptions.")

    # Diagnostic: is job_level actually usable as a fallback signal?
    if "job_level" in df.columns:
        populated = df["job_level"].notna().sum()
        print(f"      job_level populated for {populated}/{len(df)} rows "
              f"({populated / len(df) * 100:.1f}%) -- low coverage means the "
              f"experience fallback rarely engages.")
    else:
        print("      WARNING: no 'job_level' column found -- experience "
              "fallback will always use the neutral 0.65 default when text "
              "extraction fails.")

    # -- 2. Dedupe repeat postings ----------------------------------------------
    print("\n[2/7] Deduping repeat postings ...")
    df = dedupe_jobs(df)

    # -- 3. Load Sentence Transformer --------------------------------------------
    print(f"\n[3/7] Loading embedding model '{EMBEDDING_MODEL}' ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL)

    # -- 4. Derive candidate skills + embed resume -------------------------------
    print("\n[4/7] Deriving candidate skills and embedding resume ...")
    candidate_skills_lower = extract_skills_from_text(CANDIDATE_RESUME_TEXT)
    print(f"      Detected {len(candidate_skills_lower)} candidate skills from "
          f"resume text using shared vocabulary: "
          f"{', '.join(sorted(candidate_skills_lower))}")

    resume_embedding = model.encode(
        [CANDIDATE_RESUME_TEXT.strip()],
        normalize_embeddings=True,
        show_progress_bar=False
    )

    # -- 5. Score every JD --------------------------------------------------------
    print(f"\n[5/7] Scoring {len(df)} job descriptions ...")

    match_texts = [
        build_match_text(row.get("title", ""), row.get("description", ""))
        for _, row in df.iterrows()
    ]

    jd_embeddings = model.encode(
        match_texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=64
    )

    sim_scores = (resume_embedding @ jd_embeddings.T)[0]

    # Min-max normalize within this batch (v2 Fix #1, unchanged) so the 0-100
    # scale (and the Excellent/Strong/... labels) reflect relative fit for
    # THIS run, rather than assuming raw cosine similarity spans 0-1 (it
    # typically clusters ~0.3-0.6 even for strong matches).
    sim_min, sim_max = sim_scores.min(), sim_scores.max()
    if sim_max > sim_min:
        sim_scores_normalized = (sim_scores - sim_min) / (sim_max - sim_min)
    else:
        sim_scores_normalized = np.zeros_like(sim_scores)  # degenerate case: all identical

    print(f"      Raw semantic similarity range: {sim_min:.3f} - {sim_max:.3f} "
          f"(normalized to 0-1 for scoring)")

    print("      Computing weighted skill overlap, experience, domain, and "
          "location fit per job ...")

    skill_scores, exp_scores, domain_scores, location_scores = [], [], [], []
    jd_skill_list = []

    for (i, row), match_text in zip(df.iterrows(), match_texts):
        desc = str(row.get("description", ""))
        job_level = str(row.get("job_level", ""))
        company_industry = str(row.get("company_industry", ""))
        location = row.get("location", "")
        is_remote = row.get("is_remote", "")

        jd_skills_lower = extract_skills_from_text(match_text)

        skill_j = weighted_jaccard_skill_score(candidate_skills_lower, jd_skills_lower)
        exp_j = experience_fit_score(CANDIDATE_YOE, desc, job_level)
        domain_j = domain_fit_score(match_text, company_industry)
        location_j = location_fit_score(location, is_remote)

        skill_scores.append(skill_j)
        exp_scores.append(exp_j)
        domain_scores.append(domain_j)
        location_scores.append(location_j)
        jd_skill_list.append(", ".join(sorted(jd_skills_lower)))

    # -- 6. Assemble results -------------------------------------------------
    print("\n[6/7] Assembling ranked results ...")

    df["semantic_score"] = (sim_scores_normalized * 100).round(2)
    df["semantic_score_raw"] = (sim_scores * 100).round(2)  # kept for reference/debugging
    df["skill_score"] = (np.array(skill_scores) * 100).round(2)
    df["exp_score"] = (np.array(exp_scores) * 100).round(2)
    df["domain_score"] = (np.array(domain_scores) * 100).round(2)
    df["location_score"] = (np.array(location_scores) * 100).round(2)
    df["match_score"] = [
        compute_final_score(s, sk, e, d, l)
        for s, sk, e, d, l in zip(
            sim_scores_normalized, skill_scores, exp_scores,
            domain_scores, location_scores
        )
    ]
    df["match_label"] = df["match_score"].apply(score_label)
    df["jd_skills_found"] = jd_skill_list

    def overlap(jd_skills_str: str) -> str:
        jd = set(jd_skills_str.split(", ")) if jd_skills_str else set()
        overlap_set = candidate_skills_lower & jd
        return ", ".join(sorted(overlap_set))

    df["skill_overlap"] = df["jd_skills_found"].apply(overlap)

    df = df.sort_values("match_score", ascending=False).reset_index(drop=True)
    df.index += 1  # 1-based rank

    output_cols = [
        "match_score", "match_label",
        "semantic_score", "semantic_score_raw", "skill_score", "exp_score",
        "domain_score", "location_score",
        "title", "company", "location", "site", "date_posted",
        "job_level", "is_remote", "job_url",
        "skill_overlap", "jd_skills_found",
        "description",
    ]
    output_cols = [c for c in output_cols if c in df.columns]  # tolerate missing optional cols
    df[output_cols].to_csv(OUTPUT_CSV, index_label="rank")
    print(f"      Saved all {len(df)} scored jobs -> {OUTPUT_CSV}")

    top_df = df.head(TOP_N)
    top_records = []
    for _, row in top_df.iterrows():
        top_records.append({
            "rank": int(row.name),
            "match_score": float(row["match_score"]),
            "match_label": row["match_label"],
            "semantic_score": float(row["semantic_score"]),
            "skill_score": float(row["skill_score"]),
            "exp_score": float(row["exp_score"]),
            "domain_score": float(row["domain_score"]),
            "location_score": float(row["location_score"]),
            "title": str(row.get("title", "")),
            "company": str(row.get("company", "")),
            "location": str(row.get("location", "")),
            "site": str(row.get("site", "")),
            "date_posted": str(row.get("date_posted", "")),
            "job_level": str(row.get("job_level", "")),
            "is_remote": str(row.get("is_remote", "")),
            "job_url": str(row.get("job_url", "")),
            "skill_overlap": str(row.get("skill_overlap", "")),
            "description": str(row.get("description", ""))[:2000],
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(top_records, f, indent=2)
    print(f"      Saved top {TOP_N} jobs -> {OUTPUT_JSON}")

    # -- 7. Print top-15 summary table ----------------------------------------
    print("\n" + "=" * 70)
    print(f"TOP 15 MATCHED JOBS (YOE: {CANDIDATE_YOE})")
    print("=" * 70)
    print(f"{'Rank':<5} {'Score':<7} {'Label':<11} {'Title':<38} {'Company':<25} {'Location'}")
    print("-" * 120)

    for rank, row in df.head(15).iterrows():
        title = str(row["title"])[:36]
        company = str(row["company"])[:23]
        location = str(row["location"])[:20]
        print(
            f"{rank:<5} {row['match_score']:<7.1f} {row['match_label']:<11} "
            f"{title:<38} {company:<25} {location}"
        )

    print("-" * 120)

    dist = {
        "Excellent (>=75)": int((df["match_score"] >= 75).sum()),
        "Strong    (60-74)": int(((df["match_score"] >= 60) & (df["match_score"] < 75)).sum()),
        "Good      (45-59)": int(((df["match_score"] >= 45) & (df["match_score"] < 60)).sum()),
        "Fair      (30-44)": int(((df["match_score"] >= 30) & (df["match_score"] < 45)).sum()),
        "Weak      (<30)": int((df["match_score"] < 30).sum()),
    }
    print("\nScore Distribution:")
    for label, count in dist.items():
        bar = "#" * count
        print(f"  {label}: {count:>3}  {bar[:60]}")

    print("\nOutput files:")
    print(f"   {OUTPUT_CSV}  -> all {len(df)} jobs, ranked by score")
    print(f"   {OUTPUT_JSON} -> top {TOP_N} jobs ready for email writer")
    print("\nDone. Review the Top 15 above to validate match quality.")
    print("=" * 70)


if __name__ == "__main__":
    main()