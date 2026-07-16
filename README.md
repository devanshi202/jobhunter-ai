# JobHunter AI — Job Search Automation Platform

AI-powered platform that automates job searching, resume matching, and cold email outreach.

## Features
- [x] Phase 1: Resume Upload & AI Parsing
- [ ] Phase 2: Automated Job Scraping
- [ ] Phase 3: Semantic Resume-Job Matching
- [ ] Phase 4: AI Cold Email Generation
- [ ] Phase 5: Tracking & Automation
- [ ] Phase 6: Advanced Outreach

## Prerequisites
- Java 21+
- Python 3.12+
- PostgreSQL 18 with pgvector extension
- Ollama with llama3.1 model

## Quick Start
1. **Set up Database:**
   ```bash
   createdb job_automation
   ```
2. **Start Ollama:**
   ```bash
   brew services start ollama
   ollama pull llama3.1
   ```
3. **Start AI Service:**
   ```bash
   cd ai-service
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --port 8000
   ```
4. **Start Backend:**
   ```bash
   cd backend
   ./gradlew bootRun
   ```
5. Open http://localhost:8080 in your browser.
