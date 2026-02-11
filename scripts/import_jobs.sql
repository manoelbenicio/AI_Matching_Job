-- Import jobs_merged_final.csv into the jobs table
-- Uses a staging table to handle the extra source_file column

BEGIN;

CREATE TEMP TABLE jobs_staging (
    job_id VARCHAR(100),
    job_title VARCHAR(500),
    company_name VARCHAR(500),
    job_description TEXT,
    location VARCHAR(500),
    salary_info VARCHAR(255),
    seniority_level VARCHAR(100),
    employment_type VARCHAR(100),
    work_type VARCHAR(100),
    contract_type VARCHAR(100),
    sector VARCHAR(255),
    job_url TEXT,
    apply_url TEXT,
    company_url TEXT,
    time_posted VARCHAR(100),
    num_applicants VARCHAR(100),
    recruiter_name VARCHAR(255),
    recruiter_url TEXT,
    source_file TEXT
);

COPY jobs_staging FROM '/tmp/jobs_merged_final.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

INSERT INTO jobs (job_id, job_title, company_name, job_description, location,
                  salary_info, seniority_level, employment_type, work_type,
                  contract_type, sector, job_url, apply_url, company_url,
                  time_posted, num_applicants, recruiter_name, recruiter_url)
SELECT job_id, job_title, company_name, job_description, location,
       salary_info, seniority_level, employment_type, work_type,
       contract_type, sector, job_url, apply_url, company_url,
       time_posted, num_applicants, recruiter_name, recruiter_url
FROM jobs_staging
ON CONFLICT (job_id) DO NOTHING;

COMMIT;

SELECT COUNT(*) AS total_imported FROM jobs;
