"""
Resume bullet enhancer — rewrites resume bullets to align with JD phrasing
and surface truthful, already-demonstrated skills that map to high-demand
keywords, using your local Ollama instance (llama3.1).

IMPORTANT: This produces SUGGESTIONS for manual review, not a final resume.
Never auto-apply without reviewing.

Input:
    resume_experience.json — Structured candidate experience
    skill_frequency_ranking.csv — Generated from scraped JDs

Output:
    resume_enhancement_suggestions.json — original + suggested bullet +
    keywords considered + needs_review flag.
"""

import json
import os
import traceback
import ollama
import pandas as pd

# --- Config -----------------------------------------------------------------

OLLAMA_MODEL = "llama3.1"  # matches local Ollama model

RESUME_JSON = "resume_experience.json"
SKILL_RANKING_CSV = "skill_frequency_ranking.csv"
TOP_N_SKILLS = 25  # top in-demand skills from market JDs to consider
OUTPUT_JSON = "resume_enhancement_suggestions.json"

# --- Load inputs --------------------------------------------------------------

if not os.path.exists(RESUME_JSON):
    raise FileNotFoundError(f"Missing {RESUME_JSON}. Please create it or run resume parser first.")

with open(RESUME_JSON, "r", encoding="utf-8") as f:
    experience = json.load(f)

# Load top skills from ranking CSV or fallback to default top core skills
if os.path.exists(SKILL_RANKING_CSV):
    skill_df = pd.read_csv(SKILL_RANKING_CSV)
    top_skills = skill_df.sort_values("jd_count", ascending=False)["skill"].head(TOP_N_SKILLS).tolist()
else:
    print(f"[WARN] {SKILL_RANKING_CSV} not found. Using default market skill list.")
    top_skills = [
        "Java", "Spring Boot", "Microservices", "REST APIs", "SQL", "PostgreSQL",
        "Hibernate", "JPA", "Spring Security", "Docker", "AWS", "CI/CD",
        "Design Patterns", "Agile", "Postman", "Kafka", "Redis", "Git", "Maven"
    ]

print(f"\nTop {len(top_skills)} market-demanded skills being used as rewrite context:")
print(", ".join(top_skills))
print("=" * 70)

# --- Prompt template ----------------------------------------------------------

SYSTEM_PROMPT = """You are an expert technical resume coach and ATS optimization specialist.
Your task is to rewrite a software engineer's resume bullet point to better align with current job market phrasing and high-demand keywords, WITHOUT fabricating anything.

Rules you MUST strictly follow:
1. TRUTHFULNESS: Only incorporate a keyword from the provided list if it genuinely reflects what the original bullet already describes (e.g., if the bullet mentions building REST APIs with Spring Boot, "Microservices" or "RESTful Endpoints" is acceptable if implied — do NOT add "Kafka", "Kubernetes", or "AWS" unless the original context mentions or directly implies it).
2. ACTION-ORIENTED & IMPACT: Use strong active verbs (e.g., "Engineered", "Streamlined", "Resolved", "Architected", "Spearheaded") and preserve all original metrics (e.g., "80+ defects", "20+ Change Requests", "10+ release cycles").
3. DO NOT invent metrics, numbers, scale, or technologies not present in the original.
4. If you are uncertain whether a keyword fairly applies, leave it out and set needs_review to true with a note explaining why.
5. Return ONLY a valid JSON object with this exact structure (no markdown fences, no explanation):
{
  "rewritten": "...",
  "keywords_used": ["keyword1", "keyword2"],
  "needs_review": false,
  "notes": "Brief explanation of improvements made"
}
"""

def rewrite_bullet(company: str, role: str, original_bullet: str, skills: list[str]) -> dict:
    user_prompt = f"""Company: {company}
Role: {role}
Original Bullet: "{original_bullet}"

Market-demanded keywords to consider (incorporate only if genuinely applicable):
{', '.join(skills)}

Rewrite this bullet for maximum impact and clarity while adhering strictly to all rules. Return JSON only."""

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            # Use ollama.chat with format="json" and low temperature (same as resume_parser.py)
            response = ollama.chat(
                model=OLLAMA_MODEL,
                format="json",
                options={
                    "temperature": 0.1,
                    "num_ctx": 4096
                },
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )

            content = response["message"]["content"]
            if not content or not content.strip():
                raise ValueError("Ollama returned empty response.")

            # Clean markdown code blocks if present
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            # Ensure expected keys are present
            if "rewritten" not in parsed:
                parsed["rewritten"] = original_bullet
            if "keywords_used" not in parsed or not isinstance(parsed["keywords_used"], list):
                parsed["keywords_used"] = []
            if "needs_review" not in parsed:
                parsed["needs_review"] = False
            if "notes" not in parsed:
                parsed["notes"] = "Rewritten successfully."

            return parsed

        except Exception as e:
            if attempt == max_retries:
                return {
                    "rewritten": original_bullet,
                    "keywords_used": [],
                    "needs_review": True,
                    "notes": f"Model call failed ({e}) — original bullet preserved.",
                }

# --- Process all bullets -------------------------------------------------------

results = []
bullet_count = 0

for job in experience:
    company = job.get("company", "Company")
    role = job.get("role", "Software Engineer")
    bullets = job.get("bullets", [])

    print(f"\n🏢 Processing {company} ({role}) — {len(bullets)} bullets:")

    for bullet in bullets:
        bullet_count += 1
        suggestion = rewrite_bullet(company, role, bullet, top_skills)
        result_entry = {
            "company": company,
            "role": role,
            "original": bullet,
            "rewritten": suggestion.get("rewritten", bullet),
            "keywords_used": suggestion.get("keywords_used", []),
            "needs_review": suggestion.get("needs_review", False),
            "notes": suggestion.get("notes", "")
        }
        results.append(result_entry)

        status_tag = "[REVIEW]" if result_entry["needs_review"] else "[OK]    "
        print(f"  {status_tag} Original : {bullet[:75]}...")
        print(f"           Rewritten: {result_entry['rewritten'][:75]}...")
        if result_entry["keywords_used"]:
            print(f"           Keywords : {', '.join(result_entry['keywords_used'])}")

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

flagged = sum(1 for r in results if r["needs_review"])

print("\n" + "=" * 70)
print(f"✅ Enhancement Complete!")
print(f"   Total bullets processed : {len(results)}")
print(f"   Accepted enhancements   : {len(results) - flagged}")
print(f"   Flagged for review      : {flagged}")
print(f"   Saved suggestions to    : {OUTPUT_JSON}")
print("=" * 70)