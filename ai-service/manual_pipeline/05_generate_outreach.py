"""
05_generate_outreach.py — Cold Email & LinkedIn Connection Note Generator

Generates both:
1. Tailored cold email drafts (<120 words) with verified recipient emails and apply links.
2. Short LinkedIn connection notes (<280 chars) for personalized recruiter outreach.

Uses local Ollama (llama3.1) and outputs to:
- output/email_drafts.json
- output/email_drafts_preview.md
- output/connection_notes.json
- output/connection_notes_preview.md
"""

import json
from pathlib import Path
import ollama
import config

# ---------------------------------------------------------------------------
# PROMPTS
# ---------------------------------------------------------------------------

EMAIL_SYSTEM_PROMPT = f"""You are an elite executive career coach and cold outreach specialist who writes ultra-effective, concise, professional cold emails to tech hiring managers and recruiters.

Candidate profile:
- Name: {config.CANDIDATE_NAME}
- Role: Software Engineer / Java Backend Developer (2.5+ YOE)
- Current Company: Tata Consultancy Services (TCS) working on Société Générale's Capital Markets platform (TCS BaNCS)
- Core Backend Stack: Java, Spring Boot, Microservices, REST APIs, SQL, PostgreSQL, Hibernate, Docker, AWS, CI/CD, Agile
- AI/Applied ML Stack: LLM integration (Ollama/llama3.1), semantic search, vector embeddings (pgvector, sentence-transformers), FastAPI, prompt engineering
- Key Metrics (backend/production): Resolved 80+ production-impacting defects via root cause analysis; delivered 20+ client change requests across 10+ release cycles.
- Key Metrics (AI project): Architected a personal LLM-based job-matching platform that cut manual screening effort by ~95% and increased job discovery volume 40x.

The candidate has proven experience ONLY in the technologies listed above. Do not claim, imply, or invent experience with any technology, tool, or domain not listed here — even if it appears in the job description. If the JD's stack barely overlaps with the profile above, still write a strong email built only on genuine overlaps plus transferable backend fundamentals; do not fabricate a match.

Rules for the email:
1. BREVITY: Keep the total body strictly UNDER 120 words.
2. NO FLUFF: Do NOT use clichéd openings like "I hope this email finds you well" or "I am writing to express my interest".
3. TAILORED VALUE: In the second paragraph, mention 2-3 technologies or requirements from the JD that genuinely appear in the candidate's proven stack above. If the JD signals a Capital Markets / BFSI / fintech domain, lead with the Société Générale experience. If the JD signals AI/LLM/ML engineering, lead with the AI project metrics instead. Never mention both angles in one email — pick whichever the JD supports better.
4. LOW-FRICTION CTA: End with a polite, specific request for a brief 10-minute introductory conversation.
5. SALUTATION: If a recruiter or contact name is provided in the user message, use "Hi [FirstName],". If no name is provided, use "Hi Hiring Team,". Never output literal bracket placeholders.
6. SUBJECT LINE: Under 8 words, no clickbait, no emojis.
7. OUTPUT FORMAT: Respond with ONLY the raw JSON object below — no markdown code fences, no preamble, no explanation text before or after it.

{{
  "subject": "Concise high-open-rate subject line",
  "salutation": "Hi [Name] or Hi Hiring Team,",
  "body": "Paragraph 1 (Hook)\\n\\nParagraph 2 (Relevant Experience & Metric)\\n\\nParagraph 3 (Call to Action)",
  "signoff": "Best regards,\\n{config.CANDIDATE_NAME}\\n{config.CANDIDATE_EMAIL} | {config.CANDIDATE_LOCATION}"
}}
"""

NOTE_SYSTEM_PROMPT = f"""You write extremely short, warm, non-salesy LinkedIn connection request notes sent by a job applicant to a recruiter or engineering manager.

Sender: {config.CANDIDATE_NAME}, Java Backend Software Engineer with 2.5+ years experience at TCS in Capital Markets (Société Générale).

Rules:
1. SENDER PERSPECTIVE: The note must be written FROM {config.CANDIDATE_NAME} TO the recruiter/team at the company. Do NOT address the candidate.
2. HARD LIMIT: under 280 characters total, including spaces.
3. Reference their company and the specific role naturally.
4. Tone: brief, genuine, professional.
5. Example: "Hi! I noticed the Java Backend opening at Bluehost. With 2.5+ yrs building enterprise Java & Spring Boot microservices at TCS, I'd love to connect and follow your team's work."
6. Output ONLY the note text, nothing else -- no quotes, no explanation.
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
            model=config.OLLAMA_MODEL,
            format="json",
            options={"temperature": config.OLLAMA_TEMPERATURE, "num_ctx": 4096},
            messages=[
                {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
        content = response["message"]["content"].strip()
        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        return json.loads(content.strip())
    except Exception as e:
        print(f"      [WARN] Email fallback for {company}: {e}")
        return {
            "subject": f"{config.CANDIDATE_NAME} — Java Backend Engineer (2.5 YOE) — {title}",
            "salutation": f"Hi {recruiter},",
            "body": (
                f"I came across the {title} opening at {company} and wanted to reach out directly.\n\n"
                f"I bring 2.5+ years of experience engineering enterprise Java and Spring Boot applications in the Capital Markets domain at TCS (Société Générale). My background centers on building microservices, developing REST APIs, and resolving 80+ production defects through deep root-cause analysis.\n\n"
                f"Given {company}'s engineering focus, I'd love to connect. Would you be open to a brief 10-minute conversation this week?"
            ),
            "signoff": f"Best regards,\n{config.CANDIDATE_NAME}\n{config.CANDIDATE_EMAIL} | {config.CANDIDATE_LOCATION}"
        }

def draft_connection_note(company: str, title: str) -> str:
    prompt = f"Write a connection note for someone at {company} regarding their {title} opening."
    try:
        response = ollama.chat(
            model=config.OLLAMA_MODEL,
            options={"temperature": 0.4},
            messages=[
                {"role": "system", "content": NOTE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        note = response["message"]["content"].strip().strip('"')
        if len(note) > config.MAX_NOTE_CHARS:
            note = note[:config.MAX_NOTE_CHARS].rsplit(" ", 1)[0] + "..."
        return note
    except Exception as e:
        return f"Hi, I noticed the {title} opening at {company} and would love to connect with your engineering team."

def run_outreach():
    print("=" * 70)
    print("✉️ STEP 5: AI COLD OUTREACH DRAFTING (Emails + LinkedIn Notes)")
    print("=" * 70)

    if not config.TOP_MATCHES_JSON.exists():
        print(f"❌ Missing {config.TOP_MATCHES_JSON}. Run match_jobs first.")
        return

    with open(config.TOP_MATCHES_JSON, "r", encoding="utf-8") as f:
        matches = json.load(f)

    contacts_map = {}
    if config.CONTACTS_JSON.exists():
        with open(config.CONTACTS_JSON, "r", encoding="utf-8") as f:
            contacts_list = json.load(f)
            contacts_map = {c.get("rank"): c for c in contacts_list}

    target_jobs = matches[:config.DRAFTS_COUNT]
    print(f"Drafting outreach for top {len(target_jobs)} opportunities using Ollama ({config.OLLAMA_MODEL})...\n")

    email_drafts = []
    connection_notes = []

    email_preview_md = f"# ✉️ AI-Generated Cold Outreach Email Drafts\n\nTailored for **{config.CANDIDATE_NAME}** (2.5 YOE, Java Backend Developer)\n\n---\n\n"
    notes_preview_md = f"# 🤝 LinkedIn Connection Notes (<280 chars)\n\n---\n\n"

    for idx, job in enumerate(target_jobs, start=1):
        rank = job.get("rank", idx)
        company = job.get("company", "Company")
        title = job.get("title", "Role")
        score = job.get("match_score", 0.0)
        contact = contacts_map.get(rank, {})
        recipient_email = contact.get("primary_email", "")
        apply_url = contact.get("clean_apply_url", job.get("job_url", ""))
        linkedin_search = contact.get("linkedin_search_url", "")

        print(f"[{idx:>2}/{len(target_jobs)}] Drafting outreach for {company} — {title} (Match: {score:.1f}%)...")

        # 1. Draft Email
        email = draft_email_for_job(job, contact)
        full_email = {
            "rank": rank,
            "match_score": round(score, 1),
            "company": company,
            "title": title,
            "recipient_email": recipient_email,
            "apply_url": apply_url,
            "linkedin_search_url": linkedin_search,
            "subject": email.get("subject", ""),
            "salutation": email.get("salutation", ""),
            "body": email.get("body", ""),
            "signoff": email.get("signoff", "")
        }
        email_drafts.append(full_email)

        email_preview_md += f"## #{rank}. {company} — {title} (Match Score: {score:.1f}%)\n\n"
        email_preview_md += f"- **Recipient Email**: `{recipient_email or 'Find on LinkedIn'}`\n"
        email_preview_md += f"- **Apply Link**: [Open Application Portal]({apply_url})\n"
        email_preview_md += f"- **LinkedIn Recruiter Finder**: [Find Recruiter at {company}]({linkedin_search})\n\n"
        email_preview_md += f"```text\nSubject: {full_email['subject']}\n\n{full_email['salutation']}\n\n{full_email['body']}\n\n{full_email['signoff']}\n```\n\n---\n\n"

        # 2. Draft LinkedIn Note
        note = draft_connection_note(company, title)
        connection_notes.append({
            "rank": rank,
            "company": company,
            "title": title,
            "note": note,
            "char_count": len(note)
        })

        notes_preview_md += f"### #{rank}. {company} — {title}\n"
        notes_preview_md += f"*(Length: {len(note)} chars)*\n\n> {note}\n\n---\n\n"

    # Save outputs
    with open(config.EMAIL_DRAFTS_JSON, "w", encoding="utf-8") as f:
        json.dump(email_drafts, f, indent=2)
    with open(config.EMAIL_DRAFTS_MD, "w", encoding="utf-8") as f:
        f.write(email_preview_md)

    with open(config.CONNECTION_NOTES_JSON, "w", encoding="utf-8") as f:
        json.dump(connection_notes, f, indent=2)
    with open(config.CONNECTION_NOTES_MD, "w", encoding="utf-8") as f:
        f.write(notes_preview_md)

    print("\n" + "=" * 70)
    print(f"✅ Generated outreach drafts for {len(target_jobs)} jobs!")
    print(f"   • Emails JSON : {config.EMAIL_DRAFTS_JSON}")
    print(f"   • Emails View : {config.EMAIL_DRAFTS_MD}")
    print(f"   • Notes JSON  : {config.CONNECTION_NOTES_JSON}")
    print(f"   • Notes View  : {config.CONNECTION_NOTES_MD}")
    print("=" * 70)

if __name__ == "__main__":
    run_outreach()
