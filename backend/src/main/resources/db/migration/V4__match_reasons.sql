-- V4: match reasons for ranked browse (location component removed; ranking is per location bucket)
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS domain_score FLOAT;
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS skill_overlap TEXT;
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS match_reason TEXT;
