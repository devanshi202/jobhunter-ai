-- Enable pgvector extension for embedding storage
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User's parsed resume profile
CREATE TABLE resume_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    raw_text TEXT,
    parsed_data JSONB,
    embedding VECTOR(384),
    skills TEXT[],
    experience_years FLOAT,
    preferred_roles TEXT[],
    preferred_locations TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Scraped job postings
CREATE TABLE job_postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    experience_min FLOAT,
    experience_max FLOAT,
    description TEXT,
    skills TEXT[],
    salary_range VARCHAR(100),
    job_url TEXT,
    recruiter_name VARCHAR(255),
    recruiter_email VARCHAR(255),
    posted_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT NOW(),
    embedding VECTOR(384),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(platform, external_id)
);

CREATE INDEX idx_job_posted_at ON job_postings(posted_at DESC);
CREATE INDEX idx_job_platform ON job_postings(platform);
CREATE INDEX idx_job_status ON job_postings(status);
CREATE INDEX idx_job_company ON job_postings(company_name);

-- Match scores between resume and jobs
CREATE TABLE job_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID REFERENCES resume_profiles(id),
    job_id UUID REFERENCES job_postings(id),
    semantic_score FLOAT,
    skill_overlap_score FLOAT,
    experience_fit_score FLOAT,
    overall_score FLOAT,
    callback_probability FLOAT,
    status VARCHAR(50) DEFAULT 'NEW',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(resume_id, job_id)
);

-- Hiring contacts / POCs
CREATE TABLE hiring_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES job_postings(id),
    name VARCHAR(255),
    email VARCHAR(255),
    linkedin_url TEXT,
    role VARCHAR(255),
    source VARCHAR(100),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cold emails sent
CREATE TABLE cold_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES hiring_contacts(id),
    job_match_id UUID REFERENCES job_matches(id),
    subject TEXT,
    body TEXT,
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    replied_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'QUEUED',
    follow_up_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Referral outreach tracking
CREATE TABLE referral_outreach (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES job_postings(id),
    contact_name VARCHAR(255),
    contact_linkedin TEXT,
    contact_email VARCHAR(255),
    message_sent TEXT,
    platform VARCHAR(50),
    status VARCHAR(50) DEFAULT 'SENT',
    sent_at TIMESTAMP,
    responded_at TIMESTAMP
);
