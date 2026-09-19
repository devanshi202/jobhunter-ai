from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json

from resume_parser import parse_resume
from embedding_service import generate_embedding
from email_writer import generate_cold_email
from job_scraper import router as jobspy_router

app = FastAPI(title="JobHunter AI Service")
app.include_router(jobspy_router)

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

class BatchEmbeddingRequest(BaseModel):
    texts: list[str]

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

@app.post("/api/embed-batch")
def api_embed_batch(req: BatchEmbeddingRequest):
    """Batch embeddings for match backfill (resume + JDs). MiniLM truncates
    past ~256 tokens server-side, so cap input length to bound latency."""
    try:
        from embedding_service import get_model
        model = get_model()
        texts = [(t or "")[:4000] for t in req.texts]
        vecs = model.encode(texts, normalize_embeddings=True, batch_size=32,
                            show_progress_bar=False)
        return {"embeddings": [v.tolist() for v in vecs], "dim": len(vecs[0])}
    except Exception as e:
        print(f"Error generating batch embeddings: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate batch embeddings")

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
