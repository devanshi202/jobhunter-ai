from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json

from resume_parser import parse_resume
from embedding_service import generate_embedding
from email_writer import generate_cold_email

app = FastAPI(title="JobHunter AI Service")

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ParseResumeRequest(BaseModel):
    text: str

class GenerateEmbeddingRequest(BaseModel):
    text: str

class GenerateEmailRequest(BaseModel):
    resume_summary: str
    job_title: str
    company_name: str
    job_description: str

@app.get("/health")
def health_check():
    ollama_available = False
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            ollama_available = True
    except:
        pass
    
    return {"status": "ok", "ollama_available": ollama_available}

@app.post("/api/parse-resume")
def api_parse_resume(req: ParseResumeRequest):
    try:
        result = parse_resume(req.text)
        return result
    except Exception as e:
        print(f"Error parsing resume: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse resume")

@app.post("/api/generate-embedding")
def api_generate_embedding(req: GenerateEmbeddingRequest):
    try:
        embedding = generate_embedding(req.text)
        return {"embedding": embedding}
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate embedding")

@app.post("/api/generate-email")
def api_generate_email(req: GenerateEmailRequest):
    try:
        result = generate_cold_email(
            req.resume_summary, 
            req.job_title, 
            req.company_name, 
            req.job_description
        )
        return result
    except Exception as e:
        print(f"Error generating email: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate email")

@app.on_event("startup")
async def startup_event():
    print("Starting JobHunter AI Service...")
