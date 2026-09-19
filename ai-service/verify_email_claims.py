"""
verify_email_claims.py — Fabrication guardrail for generated cold emails

Cross-checks every generated email draft's body text against your ACTUAL
resume text. Flags any specific technology/tool mentioned in a draft that
does NOT appear anywhere in your resume — these are candidates for LLM
fabrication (pulling a technology from the JD and presenting it as your own
proven experience).

This does not catch everything (it's vocabulary-based, not full semantic
fact-checking) but it will reliably catch the two failure modes seen so far:
  - naming a specific version (e.g. "Java 21") not in your resume
  - naming a whole technology (e.g. "RabbitMQ") not in your resume

Usage:
    python verify_email_claims.py
"""

import re
import json

DRAFTS_FILE = "email_drafts.json"

# Same resume text used in generate_emails.py / match_jobs.py — keep this in
# sync with whatever your actual resume currently says.
RESUME_TEXT = """
Software Engineer with 2.5+ years of experience developing and maintaining
enterprise Java backend applications in the Capital Markets domain. Skilled in
Java, Spring Boot, Microservices, SQL, REST APIs, debugging, root cause
analysis, performance optimization, and production releases in Agile
environments. Experienced with AWS, Azure, Docker, Jenkins, PostgreSQL, MySQL,
and backend engineering practices including SOLID principles and design
patterns. Currently building an AI-powered Job Search Automation platform using
Spring Boot, Python, PostgreSQL, pgvector, Docker, and Ollama.

Experience:
- Developed and maintained enterprise Java-based backend applications for a
  Capital Markets platform (TCS BaNCS) for Société Générale.
- Investigated and resolved 80+ UAT and production-impacting application issues
  through Java debugging, SQL-based data analysis, and root cause analysis.
- Implemented 20+ client-driven change requests and backend product enhancements
  across multiple Agile release cycles.
- Supported 10+ UAT and production release cycles, API validation with Postman.
- Built backend applications using Java, Spring Boot, Hibernate, Spring Security,
  REST APIs; cloud solutions on AWS and Azure; CI/CD with Jenkins.
- Built full-stack product review platform with Spring Boot, Angular, JWT,
  Spring Security, Hibernate, MySQL.

Skills:
Java, Spring Boot, Microservices, REST APIs, Spring Security, Hibernate, JPA,
SQL, PostgreSQL, MySQL, MongoDB, AWS, Azure, Docker, Jenkins, CI/CD, Git,
Maven, Agile, Scrum, SOLID, Design Patterns, Python, JavaScript, Postman,
Apache Tika, Ollama, pgvector.
"""

# Watch-list of specific technologies/version-strings worth checking for —
# add to this as you notice new ones in drafts.
WATCH_TERMS = [
    "Java 8", "Java 11", "Java 17", "Java 21",
    "Kafka", "RabbitMQ", "gRPC", "GraphQL", "WebSocket",
    "Kubernetes", "Terraform", "Redis", "Elasticsearch",
    "Node.js", "React", "Angular", "TypeScript",
    "JUnit", "Mockito", "TDD",
]

def contains_term(text: str, term: str) -> bool:
    pattern = r"\b" + re.escape(term) + r"\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
    drafts = json.load(f)

resume_terms_present = {t for t in WATCH_TERMS if contains_term(RESUME_TEXT, t)}

print(f"Watch-list terms confirmed present in your resume: "
      f"{sorted(resume_terms_present) or '(none)'}\n")
print("=" * 80)

flagged_count = 0
for draft in drafts:
    body = draft.get("body", "")
    subject = draft.get("subject", "")
    full_text = f"{subject} {body}"

    unverified = [
        t for t in WATCH_TERMS
        if contains_term(full_text, t) and t not in resume_terms_present
    ]

    if unverified:
        flagged_count += 1
        print(f"[FLAGGED] Rank {draft.get('rank')} — {draft.get('company')} "
              f"({draft.get('title')})")
        print(f"  Unverified claims: {', '.join(unverified)}")
        print(f"  --> These technologies are NOT in your resume text but "
              f"appear in this draft. Review/remove before sending.\n")

print("=" * 80)
print(f"{flagged_count} of {len(drafts)} drafts flagged for unverified "
      f"technology claims.")
if flagged_count == 0:
    print("No watch-list mismatches found — still read every draft before "
          "sending; this only catches vocabulary-based fabrication, not all "
          "possible inaccuracies (e.g. fabricated soft claims about the "
          "target company).")