"""
JD keyword-frequency analyzer — find out what the market is actually asking
for, so you can tailor your resume to match.

Reads your scraped JD CSV (swe_jobs_india_all.csv or the sample100 one),
scans each description for a vocabulary of skills/tools/concepts, and ranks
them by how many JDs mention each one. Optionally compares against your
resume text to flag gaps.

Usage:
    python analyze_jd_keywords.py
"""

import re
import pandas as pd

# --- Config ---------------------------------------------------------------

JD_CSV = "swe_jobs_india_all.csv"   # or swe_jobs_india_all.csv
RESUME_TXT = "resume.txt"                 # plain-text export of your resume

# Vocabulary to scan for — seeded from your CandidateTargetCriteria
# (core + secondary skills) plus common Java-backend-adjacent terms that
# often show up in JDs but weren't in your original list. Add/remove freely.
SKILL_VOCAB = [
    # Core (from your criteria)
    "Java", "Spring Boot", "REST API", "SQL", "Hibernate", "JPA",
    "Spring Security", "Microservices",
    # Secondary (from your criteria)
    "Python", "PostgreSQL", "MySQL", "Docker", "AWS", "Azure", "Jenkins",
    "Git", "Maven", "JWT", "JavaScript",
    # Common additions worth checking for
    "Kafka", "RabbitMQ", "Kubernetes", "GraphQL", "Redis", "Elasticsearch",
    "MongoDB", "CI/CD", "GitHub Actions", "JUnit", "Mockito", "TDD",
    "System Design", "Design Patterns", "SOLID", "Multithreading",
    "Data Structures", "Algorithms", "Spring Cloud", "Spring MVC",
    "OAuth", "gRPC", "WebSocket", "Agile", "Scrum", "JIRA", "Terraform",
    "GCP", "Lambda", "EC2", "S3", "NoSQL", "Node.js", "React",
]

# --- Load JDs ---------------------------------------------------------------

df = pd.read_csv(JD_CSV)
descriptions = df["description"].dropna().astype(str)
total_jds = len(descriptions)
print(f"Analyzing {total_jds} job descriptions...\n")


def contains_skill(text: str, skill: str) -> bool:
    """Word-boundary, case-insensitive match to avoid false positives
    (e.g. 'R' matching inside 'REST')."""
    pattern = r"\b" + re.escape(skill) + r"\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


# --- Count skill frequency across JDs ---------------------------------------

counts = {}
for skill in SKILL_VOCAB:
    matches = descriptions.apply(lambda text: contains_skill(text, skill))
    counts[skill] = matches.sum()

freq_df = pd.DataFrame(
    {"skill": counts.keys(), "jd_count": counts.values()}
)
freq_df["pct_of_jds"] = (freq_df["jd_count"] / total_jds * 100).round(1)
freq_df = freq_df.sort_values("jd_count", ascending=False)

print("=== Skill demand ranking across your scraped JDs ===")
print(freq_df.to_string(index=False))
freq_df.to_csv("skill_frequency_ranking.csv", index=False)
print("\nSaved full ranking to skill_frequency_ranking.csv")

# --- Compare against resume (if provided) -----------------------------------

try:
    with open(RESUME_TXT, "r", encoding="utf-8") as f:
        resume_text = f.read()

    print(f"\n=== Comparing against {RESUME_TXT} ===")
    resume_has = freq_df["skill"].apply(lambda s: contains_skill(resume_text, s))
    freq_df["on_resume"] = resume_has.values

    gaps = freq_df[(~freq_df["on_resume"]) & (freq_df["jd_count"] > 0)]
    gaps = gaps.sort_values("jd_count", ascending=False)

    print("\nTop skills in demand but MISSING from your resume:")
    print(gaps.head(15).to_string(index=False))
    gaps.to_csv("resume_skill_gaps.csv", index=False)
    print("\nSaved to resume_skill_gaps.csv — review before adding anything "
          "you don't actually have experience with.")

except FileNotFoundError:
    print(f"\n(No {RESUME_TXT} found — skipping resume comparison. "
          f"Save your resume as plain text with that name and rerun to "
          f"see gaps.)")