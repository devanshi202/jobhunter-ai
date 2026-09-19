"""
config.py — Central Configuration for Manual Job Search Pipeline

Easily edit your search terms, target locations, candidate profile,
and weights here. All scripts in manual_pipeline read from this file.
"""

from pathlib import Path
import json

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs" / "2026-09-17"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Shared Data Files
SCRAPED_JOBS_CSV      = OUTPUT_DIR / "swe_jobs_scraped.csv"
MATCHED_JOBS_CSV      = OUTPUT_DIR / "matched_jobs_ranked.csv"
TOP_MATCHES_JSON      = OUTPUT_DIR / "top_matches.json"
RESOLVED_APPLY_CSV    = OUTPUT_DIR / "resolved_apply_links.csv"
RESOLVED_APPLY_JSON   = OUTPUT_DIR / "resolved_apply_links.json"
CONTACTS_CSV          = OUTPUT_DIR / "contacts_summary.csv"
CONTACTS_JSON         = OUTPUT_DIR / "company_contacts.json"
EMAIL_DRAFTS_JSON     = OUTPUT_DIR / "email_drafts.json"
EMAIL_DRAFTS_MD       = OUTPUT_DIR / "email_drafts_preview.md"
CONNECTION_NOTES_JSON = OUTPUT_DIR / "connection_notes.json"
CONNECTION_NOTES_MD   = OUTPUT_DIR / "connection_notes_preview.md"

# Path to system resume profile if synced
SYSTEM_RESUME_JSON    = BASE_DIR.parent / "resume_profile.json"

# ---------------------------------------------------------------------------
# 1. SCRAPER SETTINGS
# ---------------------------------------------------------------------------

SEARCH_TERMS = [
    "Java Backend Developer",
    "Java Developer",
    "Java Software Engineer",
    "Spring Boot Developer",
    "Java Microservices",
    "Java Backend Engineer",
    "SDE 2 Java",
    "Java Developer Fintech",   
    "Java AI Backend",          
]

LOCATIONS = [
    "Delhi NCR, India",
    "Gurugram, India",
    "Noida, India",
    "Bangalore, India",
    "Hyderabad, India",
    "Pune, India",
    "Remote",
]

SITES = ["linkedin", "indeed"]
RESULTS_PER_QUERY = 15   # modest per term/loc to avoid rate limits
HOURS_OLD = 48           # jobs posted within last 3 days

# ---------------------------------------------------------------------------
# 2. CANDIDATE PROFILE & TARGETS
# ---------------------------------------------------------------------------
CANDIDATE_NAME = "Devanshi Sharma"
CANDIDATE_YOE = 2.5
CANDIDATE_EMAIL = "sharma.devanshi.205@gmail.com"
CANDIDATE_LOCATION = "Gurugram, India"
CANDIDATE_LINKEDIN = "https://www.linkedin.com/in/devanshi-sharma-958887192/"
CANDIDATE_GITHUB = "https://github.com/devanshi202"

CANDIDATE_RESUME_TEXT = """
Software Engineer with 2.5+ years of experience building and maintaining
enterprise Java backend applications in the Capital Markets domain. Skilled in
Java, Spring Boot, Microservices, REST APIs, SQL, debugging, root cause
analysis, and performance optimization across Agile release cycles.
Experienced with AWS, Azure, Docker, Jenkins, PostgreSQL, and backend
engineering practices including SOLID principles and design patterns. Extends
this into applied AI engineering — architected a production-style LLM platform
using Spring Boot, FastAPI, Ollama, pgvector, and sentence-transformers,
implementing semantic matching over vector embeddings that cut manual
screening effort by 95%. Seeking Java Backend / Software Engineer roles
focused on scalable backend, distributed systems, and AI-integrated services.

Experience:
- Develop and maintain enterprise Java-based backend applications for
  Société Générale's Capital Markets platform using TCS BaNCS.
- Investigated and resolved 80+ UAT and production-impacting application issues
  through Java debugging, SQL-based data analysis, application log analysis,
  and detailed root cause analysis.
- Implemented 20+ client-driven change requests and backend product
  enhancements across multiple release cycles, translating functional
  requirements into reliable application changes.
- Collaborated with business users, QA teams, and client stakeholders in
  Agile delivery environments to analyze requirements, validate solutions,
  and improve release quality.
- Supported 10+ UAT and production release cycles, performing API validation
  with Postman, troubleshooting release blockers, and contributing to
  application stability.
- Participated in code reviews, defect triaging, and technical solution
  discussions to maintain code quality and reliable backend functionality.
- Improved application performance by identifying inefficient processing
  paths and implementing optimizations during issue resolution and feature
  enhancements.
- Built backend applications using Java, Spring Boot, Hibernate, Spring Security,
  REST APIs; cloud solutions on AWS and Azure; CI/CD with Jenkins.
- Developed backend features for catalogue management at Blinkit.
- Built AI-powered Job Search Automation using Spring Boot, Python, PostgreSQL,
  pgvector, Ollama; implemented semantic job matching with vector embeddings.
- Built full-stack product review platform with Spring Boot, Angular, JWT,
  Spring Security, Hibernate, MySQL.

Skills:
Java, Spring Boot, Spring MVC, Spring Security, Microservices, REST APIs, JWT,
Hibernate, JPA, SQL, PostgreSQL, MySQL, MongoDB, AWS, Azure, Docker, CI/CD,
Jenkins, Git, Maven, LLM Integration, Ollama, Semantic Search, Vector
Embeddings, sentence-transformers, pgvector, Prompt Engineering, FastAPI,
Apache Tika, Web Scraping, SOLID Principles, Design Patterns, Data Structures
& Algorithms, Code Review, Debugging, Root Cause Analysis, Performance
Optimization, Python, JavaScript, React, Angular, Agile, Scrum, JIRA, API
Testing, Postman, Log Analysis.
"""

# ---------------------------------------------------------------------------
# 3. MATCHING ENGINE WEIGHTS (match_job_v3 5-component scoring)
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_N_MATCHES   = 25

MATCH_WEIGHTS = {
    "semantic": 0.40,   # sentence-transformers cosine similarity
    "skill":    0.25,   # weighted Jaccard skill overlap
    "exp":      0.15,   # smooth YOE distance penalty
    "domain":   0.10,   # Capital Markets / BFSI / Fintech bonus
    "location": 0.10,   # Delhi-NCR / Gurugram / Remote bonus
}

# ---------------------------------------------------------------------------
# 4. LLM SETTINGS (Ollama)
# ---------------------------------------------------------------------------
OLLAMA_MODEL = "llama3.1"
OLLAMA_TEMPERATURE = 0.2
DRAFTS_COUNT = 10
MAX_NOTE_CHARS = 280
