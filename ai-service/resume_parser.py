import json
import ollama
import traceback

def parse_resume(raw_text: str) -> dict:

    print(f"[DEBUG] org len of raw_text {len(raw_text)}")
    max_chars = 12000
    if len(raw_text) > max_chars:
        print(f"[DEBUG] Resume text truncated from {len(raw_text)} to {max_chars} chars.")
        raw_text = raw_text[:max_chars]

    
    prompt = f"""
You are an expert resume parser. Analyze the following resume text carefully and extract structured information.

RESUME TEXT:
{raw_text}

Instructions:
1. Preserve verbatim accuracy for text extraction. For professional summary, keep 3-5 sentences reflecting candidate's original text directly.
2. Check the "Extracted Hyperlinks from Document" section or resume text for LinkedIn and GitHub URLs.
3. For preferred_roles, extract all targetable job roles suggested by this candidate's skills and experience.
4. For preferred_locations, include current location and Remote, plus any mentioned locations.

Extract the following information and return ONLY valid JSON (no markdown formatting, no explanation, no backticks).
Ensure the output matches this exact JSON schema:
{{
  "name": "full name (string)",
  "email": "email address (string)",
  "phone": "phone number (string)",
  "current_location": "current location (string)",
  "linkedin_url": "full linkedin profile url (string)",
  "github_url": "full github profile url (string)",
  "experience_years": 0.0,
  "current_role": "most recent job title (string)",
  "skills": ["skill1", "skill2"],
  "experience": [
    {{"company": "name", "role": "title", "duration": "period", "description": "key achievements"}}
  ],
  "projects": [
    {{"title": "name", "technologies": ["tech1"], "description": "what was built"}}
  ],
  "education": ["degree - university"],
  "achievements": ["award1", "achievement2"],
  "preferred_roles": ["targeted role 1", "targeted role 2"],
  "preferred_locations": ["current location", "Remote"],
  "summary": "3-5 sentence verbatim or high-fidelity professional summary (string)"
}}
"""

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[DEBUG] Attempt {attempt}/{max_retries}: Sending request to Ollama...")
            
            # Pass format="json" and options to constrain output
            response = ollama.chat(
                model="llama3.1",
                format="json",  # FORCES OLLAMA TO RETURN STRICT VALID JSON
                options={
                    "temperature": 0.1,  # Low temperature = reliable output
                    "num_ctx": 4096      # Ensure context window is large enough
                },
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response['message']['content']
            
            # Print raw response to terminal for quick debugging
            print("\n--- [DEBUG] RAW OLLAMA RESPONSE START ---")
            print(repr(content))
            print("--- [DEBUG] RAW OLLAMA RESPONSE END ---\n")
            
            if not content or not content.strip():
                raise ValueError("Ollama returned an empty response string.")
                
            # Clean Markdown formatting if present
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()

            # Attempt parsing JSON
            parsed_json = json.loads(cleaned_content)
            print("[DEBUG] Successfully parsed JSON from Ollama!")
            return parsed_json

        except Exception as e:
            print(f"[ERROR] Attempt {attempt} failed: {e}")
            if attempt == max_retries:
                print("[ERROR] Max retries reached. Printing full stack trace:")
                traceback.print_exc()
        
    
        print("[WARN] Returning fallback empty resume schema.")
        # Fallback empty response
        return {
            "name": "Unknown",
            "email": "",
            "phone": "",
            "current_location": "",
            "linkedin_url": "",
            "github_url": "",
            "experience_years": 0.0,
            "current_role": "Unknown",
            "skills": [],
            "experience": [],
            "projects": [],
            "education": [],
            "achievements": [],
            "preferred_roles": [],
            "preferred_locations": [],
            "summary": "Failed to parse resume automatically."
        }
