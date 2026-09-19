-- V2: JobSpy CSV browse support (search_location/search_term/platform drill-down + detail fields)
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS job_url_direct TEXT;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS job_type VARCHAR(100);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS job_level VARCHAR(100);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS job_function VARCHAR(500);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS emails TEXT;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS company_industry VARCHAR(255);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS company_url TEXT;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS company_url_direct TEXT;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS company_addresses TEXT;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS company_num_employees VARCHAR(100);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS company_revenue VARCHAR(100);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS company_description TEXT;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS search_term VARCHAR(255);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS search_location VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_job_search_location ON job_postings(search_location);
CREATE INDEX IF NOT EXISTS idx_job_search_term ON job_postings(search_term);
CREATE INDEX IF NOT EXISTS idx_job_company_title ON job_postings(company_name, title);
