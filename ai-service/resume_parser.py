import json
import ollama
import traceback

def parse_resume(raw_text: str) -> dict:
    prompt = f"""
You are a professional resume parser. Analyze the following resume text and extract structured information.

RESUME TEXT:
{raw_text}

Extract the following information and return ONLY valid JSON (no markdown formatting, no explanation, no backticks).
Ensure the output matches this exact JSON schema:
{{
  "name": "full name (string)",
  "email": "email address (string)",
  "phone": "phone number (string)",
  "experience_years": 0.0,
  "current_role": "most recent job title (string)",
  "skills": ["skill1", "skill2"],
  "experience": [
    {{"company": "name", "role": "title", "duration": "period", "description": "key achievements"}}
  ],
  "education": ["degree - university"],
  "preferred_roles": ["inferred from experience (string)"],
  "preferred_locations": ["if mentioned (string)"],
  "summary": "2-3 sentence professional summary (string)"
}}
"""

    try:
        response = ollama.chat(
            model="llama3.1",
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response['message']['content'].strip()
        
        # Clean up if LLM included markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        return json.loads(content)
        
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        traceback.print_exc()
        
        # Fallback empty response
        return {
            "name": "Unknown",
            "email": "",
            "phone": "",
            "experience_years": 0.0,
            "current_role": "Unknown",
            "skills": [],
            "experience": [],
            "education": [],
            "preferred_roles": [],
            "preferred_locations": [],
            "summary": "Failed to parse resume automatically."
        }
