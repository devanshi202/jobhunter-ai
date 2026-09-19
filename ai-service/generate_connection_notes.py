"""
generate_connection_notes.py — Personalized LinkedIn connection note generator

Generates short, personalized connection-request notes (LinkedIn's limit is
~300 characters) for each of your top-matched companies, using your local
Ollama instance. These are meant to be copy-pasted manually when you send
each connection request yourself — this script does NOT send anything or
touch LinkedIn automatically, by design (see conversation context on why).

Input:
    top_matches.json — your ranked job matches

Output:
    connection_notes.json — one short note per company, ready to paste
    connection_notes_preview.md — readable version for quick copy-paste
"""

import json
import ollama

MATCHES_FILE = "top_matches.json"
OUTPUT_JSON = "connection_notes.json"
OUTPUT_PREVIEW = "connection_notes_preview.md"

OLLAMA_MODEL = "llama3.1"
NOTES_COUNT = 10
MAX_CHARS = 280  # stay safely under LinkedIn's ~300 char connection note limit

SYSTEM_PROMPT = """You write extremely short, warm, non-salesy LinkedIn
connection request notes.

Candidate: Devanshi Sharma, Java Backend Software Engineer, 2.5+ years
experience, currently at TCS working on a Capital Markets platform.

Rules:
1. HARD LIMIT: under 280 characters total, including spaces. This is not
   negotiable -- LinkedIn truncates longer notes.
2. No generic filler ("I'd love to connect!", "Hope you're doing well").
3. Reference the specific role/company naturally, in one clause.
4. Tone: brief, genuine, professional -- like a real person, not a template.
5. Do NOT claim any specific skill/technology that isn't plainly Java/Spring
   Boot/backend engineering -- keep it generic about backend experience,
   since this is a first-touch note, not a full pitch.
6. Output ONLY the note text, nothing else -- no quotes, no explanation.
"""

def generate_note(company: str, title: str) -> str:
    prompt = f"Write a connection note for someone at {company} regarding their {title} opening."
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            options={"temperature": 0.4},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        note = response["message"]["content"].strip().strip('"')
        if len(note) > MAX_CHARS:
            note = note[:MAX_CHARS].rsplit(" ", 1)[0] + "..."
        return note
    except Exception as e:
        return f"[Generation failed: {e} -- write manually for {company}]"


def main():
    with open(MATCHES_FILE, "r", encoding="utf-8") as f:
        matches = json.load(f)

    targets = matches[:NOTES_COUNT]
    results = []
    preview_md = "# LinkedIn Connection Notes (copy-paste manually)\n\n"

    for job in targets:
        company = job.get("company", "Company")
        title = job.get("title", "Role")
        note = generate_note(company, title)

        results.append({
            "rank": job.get("rank"),
            "company": company,
            "title": title,
            "note": note,
            "char_count": len(note),
        })

        preview_md += f"### {company} — {title}\n"
        preview_md += f"({len(note)} chars)\n\n> {note}\n\n---\n\n"

        print(f"[{job.get('rank')}] {company}: {note} ({len(note)} chars)")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    with open(OUTPUT_PREVIEW, "w", encoding="utf-8") as f:
        f.write(preview_md)

    print(f"\nSaved {len(results)} notes to {OUTPUT_JSON} and {OUTPUT_PREVIEW}")
    print("Copy each note manually into LinkedIn's connection-request dialog "
          "when you send the request yourself.")


if __name__ == "__main__":
    main()