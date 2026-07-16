import json
import ollama

def generate_cold_email(resume_summary: str, job_title: str, company_name: str, job_description: str) -> dict:
    prompt = f"""
You are writing a cold email to a hiring manager for the following job:
Company: {company_name}
Job Title: {job_title}
Job Description: {job_description}

Candidate Profile (This is YOU):
{resume_summary}

Write a professional, concise cold email (under 150 words) that:
1. Opens with something specific about the company or the role
2. Highlights 2-3 highly relevant skills/achievements from the candidate's profile
3. Connects them directly to the job requirements
4. Ends with a clear call-to-action (e.g. asking for a brief chat)
5. Tone: confident but not arrogant, professional but human

Do NOT use generic phrases like "I am writing to express my interest in..."

Return ONLY a JSON object with this exact format (no markdown formatting, no explanation):
{{
  "subject": "The suggested email subject line",
  "body": "The complete email body"
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
        print(f"Error calling Ollama for email generation: {e}")
        
        # Fallback response
        return {
            "subject": f"Application for {job_title} position",
            "body": f"Hi Hiring Manager,\n\nI am very interested in the {job_title} role at {company_name}. Please find my resume attached.\n\nBest regards,"
        }
