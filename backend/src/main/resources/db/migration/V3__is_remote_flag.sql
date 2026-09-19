-- V3: portal is_remote flag (union Remote bucket = search_location 'Remote' OR is_remote true)
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS is_remote BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_job_is_remote ON job_postings(is_remote);
