"""
generate_emails.py — AI Cold Email Generator for Matched Opportunities

Takes:
1. top_matches.json (Ranked jobs with skill overlaps and JD descriptions)
2. company_contacts.json (Verified emails, domains, and recruiter URLs)
3. Enhanced candidate profile (Devanshi Sharma, 2.5 YOE, Java Backend)

Calls local Ollama (llama3.1) to draft hyper-tailored, high-converting, concise (<120 words)
cold emails that highlight truthful alignment with each specific JD.

Outputs:
    email_drafts.json          — Structured drafts for review & sending
    email_drafts_preview.md    — Formatted Markdown document for instant reading
"""

import json
import os
import re
from pathlib import Path
import ollama

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

MATCHES_FILE   = "top_matches.json"
CONTACTS_FILE  = "company_contacts.json"
OUTPUT_JSON    = "email_drafts.json"
OUTPUT_PREVIEW = "email_drafts_preview.md"

OLLAMA_MODEL = "llama3.1"
DRAFTS_COUNT = 10   # generate drafts for top 10 matched jobs

# Candidate Profile
PROFILE_JSON = "resume_profile.json"

def load_candidate_profile() -> dict:
    if Path(PROFILE_JSON).exists():
        try:
            with open(PROFILE_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "name": data.get("name", "Devanshi Sharma"),
                "email": data.get("email", "sharma.devanshi.205@gmail.com"),
                "phone": data.get("phone", ""),
                "current_role": data.get("current_role", "Software Engineer (Java Backend)"),
                "experience_years": f"{data.get('experience_years', 2.5)}+",
                "summary": data.get("summary", ""),
                "skills": data.get("skills", []),
                "key_highlights": [
                    f"{data.get('experience_years', 2.5)}+ years building and maintaining enterprise Java backend applications in Capital Markets domain at TCS (Société Générale / TCS BaNCS).",
                    "Investigated and resolved 80+ UAT and production defects through Java debugging, SQL analysis, and root cause analysis.",
                    "Delivered 20+ client Change Requests and backend enhancements across multiple Agile release cycles.",
                    "Built microservices and REST APIs with Spring Boot, Spring Security, Hibernate/JPA, PostgreSQL, and MySQL.",
                    "Hands-on with AWS, Azure, Docker, Jenkins CI/CD, Postman, and Git."
                ]
            }
        except Exception as e:
            print(f"[WARN] Could not load {PROFILE_JSON}: {e}")

    return {
        "name": "Devanshi Sharma",
        "email": "sharma.devanshi.205@gmail.com",
        "phone": "",
        "current_role": "Software Engineer (Java Backend)",
        "experience_years": "2.5+",
        "summary": "Software Engineer with 2.5+ years of experience in Java backend development.",
        "skills": ["Java", "Spring Boot", "Microservices", "SQL", "AWS", "Docker"],
        "key_highlights": [
            "2.5+ years building enterprise Java backend applications at TCS (Société Générale / TCS BaNCS).",
            "Investigated and resolved 80+ UAT and production defects through root cause analysis.",
            "Delivered 20+ client Change Requests across Agile release cycles.",
            "Built microservices with Spring Boot, Hibernate, PostgreSQL, Docker, AWS."
        ]
    }

CANDIDATE = load_candidate_profile()

SYSTEM_PROMPT = """You are an elite executive career coach and cold outreach specialist who writes ultra-effective, concise, professional cold emails to tech hiring managers and recruiters.

Candidate profile:
- Name: Devanshi Sharma
- Role: Software Engineer / Java Backend Developer (2.5+ YOE)
- Current Company: Tata Consultancy Services (TCS) working on Société Générale's Capital Markets platform (TCS BaNCS)
- Core Stack: Java, Spring Boot, Microservices, REST APIs, SQL, PostgreSQL, Hibernate, Docker, AWS, CI/CD, Agile
- Key Metrics: Resolved 80+ production-impacting defects via root cause analysis; delivered 20+ client change requests across 10+ release cycles.

Rules for the email:
1. BREVITY: Keep the total body strictly UNDER 120 words. Hiring managers discard long emails.
2. NO FLUFF: Do NOT use clichéd openings like "I hope this email finds you well" or "I am writing to express my interest".
3. TAILORED VALUE: In the second paragraph, mention 2-3 specific technologies from their JD that Devanshi has proven experience with (e.g. Java, Spring Boot, Microservices, SQL, AWS/Docker).
4. LOW-FRICTION CTA: End with a polite, specific request for a brief 10-minute introductory conversation.
5. JSON OUTPUT: Respond ONLY with valid JSON in this exact structure:
{
  "subject": "Concise high-open-rate subject line",
  "salutation": "Hi [Name / Hiring Team],",
  "body": "Paragraph 1 (Hook)\\n\\nParagraph 2 (Relevant Experience & Metric)\\n\\nParagraph 3 (Call to Action)",
  "signoff": "Best regards,\\nDevanshi Sharma\\nsharma.devanshi.205@gmail.com | Gurugram, India"
}
"""

def draft_email_for_job(job: dict, contact: dict) -> dict:
    company = job.get("company", "Company")
    title   = job.get("title", "Software Engineer")
    skills  = job.get("skill_overlap", "Java, Spring Boot, Microservices, SQL")
    desc_snippet = job.get("description", "")[:1200]
    recruiter = contact.get("primary_contact_name", "Hiring Team")

    user_prompt = f"""Target Company: {company}
Role: {title}
Recruiter / Contact: {recruiter}
Overlapping Skills with Candidate: {skills}

Job Description Snippet:
{desc_snippet}

Draft a personalized, high-converting cold outreach email for this specific role and company."""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            format="json",
            options={
                "temperature": 0.2,
                "num_ctx": 4096
            },
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response["message"]["content"].strip()
        # Clean markdown wrappers if any
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        parsed = json.loads(content)
        return parsed
    except Exception as e:
        print(f"      [WARN] Ollama drafting fallback for {company}: {e}")
        # Deterministic fallback draft
        return {
            "subject": f"Devanshi Sharma — Java Backend Software Engineer (2.5 YOE) — {title}",
            "salutation": f"Hi {recruiter},",
            "body": (
                f"I came across the {title} opening at {company} and wanted to reach out directly.\n\n"
                f"I bring 2.5+ years of experience engineering enterprise Java and Spring Boot applications in the Capital Markets domain at TCS (Société Générale). My background centers on building microservices, developing REST APIs, and resolving 80+ production defects through deep root-cause analysis and SQL optimization.\n\n"
                f"Given {company}'s focus on scalable backend systems, I'd love to connect. Would you be open to a brief 10-minute conversation this week?"
            ),
            "signoff": "Best regards,\nDevanshi Sharma\nsharma.devanshi.205@gmail.com | Gurugram, India"
        }

def main():
    print("=" * 70)
    print("✉️ AI Cold Email Generator (Ollama llama3.1)")
    print("=" * 70)

    # 1. Load inputs
    if not Path(MATCHES_FILE).exists() or not Path(CONTACTS_FILE).exists():
        print(f"Missing {MATCHES_FILE} or {CONTACTS_FILE}. Please run match_jobs.py and find_contacts.py first.")
        return

    with open(MATCHES_FILE, "r", encoding="utf-8") as f:
        matches = json.load(f)

    with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
        contacts_list = json.load(f)

    contacts_by_rank = {c["rank"]: c for c in contacts_list}

    target_jobs = matches[:DRAFTS_COUNT]
    print(f"Generating tailored email drafts for Top {len(target_jobs)} opportunities...\n")

    email_drafts = []
    preview_md = "# ✉️ AI-Generated Cold Outreach Email Drafts\n\n"
    preview_md += "Tailored for **Devanshi Sharma** (2.5 YOE, Java Backend Developer)\n\n---\n\n"

    for job in target_jobs:
        rank    = job.get("rank")
        company = job.get("company", "Company")
        title   = job.get("title", "Role")
        score   = job.get("match_score", 0.0)
        contact = contacts_by_rank.get(rank, {})
        recipient_email = contact.get("primary_email", "")
        apply_url = contact.get("clean_apply_url", job.get("job_url", ""))
        linkedin_search = contact.get("linkedin_search_url", "")

        print(f"[{rank:>2}/{len(target_jobs)}] Drafting email for {company} — {title} (Match: {score:.1f}%)...")
        draft = draft_email_for_job(job, contact)

        full_draft = {
            "rank": rank,
            "match_score": round(score, 1),
            "company": company,
            "title": title,
            "recipient_name": contact.get("primary_contact_name", "Hiring Team"),
            "recipient_email": recipient_email,
            "email_source": contact.get("email_source", "None"),
            "mx_verified": contact.get("mx_valid", False),
            "clean_apply_url": apply_url,
            "linkedin_recruiter_url": linkedin_search,
            "subject": draft.get("subject", ""),
            "salutation": draft.get("salutation", "Hi Hiring Team,"),
            "body": draft.get("body", ""),
            "signoff": draft.get("signoff", "Best regards,\nDevanshi Sharma"),
            "status": "DRAFT_READY_FOR_REVIEW"
        }
        email_drafts.append(full_draft)

        # Append to preview markdown
        preview_md += f"## #{rank}. {company} — {title} (Match Score: {score:.1f}%)\n\n"
        preview_md += f"- **Recipient**: `{recipient_email or 'Find on LinkedIn'}` ({contact.get('primary_contact_name', 'Hiring Team')})\n"
        preview_md += f"- **Direct Apply Link**: [Open Application Portal]({apply_url})\n"
        preview_md += f"- **LinkedIn Recruiter Finder**: [Find Technical Recruiter at {company}]({linkedin_search})\n\n"
        preview_md += "```text\n"
        preview_md += f"Subject: {full_draft['subject']}\n\n"
        preview_md += f"{full_draft['salutation']}\n\n"
        preview_md += f"{full_draft['body']}\n\n"
        preview_md += f"{full_draft['signoff']}\n"
        preview_md += "```\n\n---\n\n"

    # Save outputs
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(email_drafts, f, indent=2)

    with open(OUTPUT_PREVIEW, "w", encoding="utf-8") as f:
        f.write(preview_md)

    print("\n" + "=" * 70)
    print(f"✅ Generated {len(email_drafts)} tailored cold email drafts!")
    print(f"   - Structured JSON : {OUTPUT_JSON}")
    print(f"   - Markdown Preview: {OUTPUT_PREVIEW}")
    print("=" * 70)

    # Print sample draft to console
    first = email_drafts[0]
    print(f"\n📄 SAMPLE PREVIEW (#1 {first['company']}):")
    print("-" * 60)
    print(f"To     : {first['recipient_email'] or '[Find on LinkedIn]'}")
    print(f"Subject: {first['subject']}")
    print("-" * 60)
    print(first['salutation'])
    print(first['body'])
    print(first['signoff'])
    print("-" * 60)

if __name__ == "__main__":
    main()
