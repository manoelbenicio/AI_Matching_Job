// === Job types matching PostgreSQL schema ===

export type JobStatus =
    | 'pending'
    | 'processing'
    | 'qualified'
    | 'enhanced'
    | 'low_score'
    | 'error'
    | 'skipped';

export interface Job {
    id: number;
    job_id: string;
    job_title: string;
    company_name: string;
    location: string | null;
    work_type: string | null;
    employment_type: string | null;
    seniority_level: string | null;
    contract_type: string | null;
    sector: string | null;
    salary_info: string | null;
    score: number | null;
    status: JobStatus;
    justification: string | null;
    detailed_score: ScoreBreakdown | null;
    skills_matched: string[] | null;
    skills_missing: string[] | null;
    error_message: string | null;
    job_url: string | null;
    apply_url: string | null;
    company_url: string | null;
    job_description: string | null;
    custom_resume_url: string | null;
    posted_date: string | null;
    time_posted: string | null;
    created_at: string;
    updated_at: string;
    version: number;
}

export interface JobsResponse {
    data: Job[];
    total: number;
    page: number;
    limit: number;
    has_more: boolean;
}

export interface JobUpdate {
    status?: JobStatus;
    score?: number | null;
    justification?: string | null;
    custom_resume_url?: string | null;
    version: number;
}

export interface JobBulkUpdate {
    ids: number[];
    status: JobStatus;
}

export interface JobStats {
    total: number;
    by_status: Record<JobStatus, number>;
    avg_score: number | null;
    high_score_count: number;
    today_count: number;
}

// === Filter types ===
export interface JobFilters {
    search: string;
    status: JobStatus[];
    work_type: string[];
    score_min: number | null;
    score_max: number | null;
}

export interface SortConfig {
    column: string;
    direction: 'asc' | 'desc';
}

// === View types ===
export type ViewMode = 'table' | 'kanban' | 'split' | 'scoring';

// === CV types ===
export interface CvVersion {
    id: number;
    job_id: number;
    version_number: number;
    content: string;
    enhanced_content: string | null;
    skills_matched: string[];
    skills_missing: string[];
    fit_score: number | null;
    created_at: string;
}

export interface CvEnhanceRequest {
    job_id: number;
    resume_text?: string;
}

export interface CvEnhanceResponse {
    enhanced_cv: string;
    diff: DiffChunk[];
    version_id: number;
    fit_score: number;
    skills_matched: string[];
    skills_missing: string[];
}

export interface DiffChunk {
    type: 'added' | 'removed' | 'unchanged';
    content: string;
}

export interface CvParseResponse {
    text: string;
    filename: string;
    size_bytes: number;
}

// === Audit types ===
export interface AuditEvent {
    id: number;
    job_id: number;
    action: string;
    field: string | null;
    old_value: string | null;
    new_value: string | null;
    created_at: string;
}

// === Pipeline types ===
export interface PipelineStage {
    id: string;
    name: string;
    order: number;
    color: string;
    wip_limit: number | null;
}

// Pipeline stages (initial — matching existing DB enum)
export const PIPELINE_STAGES: PipelineStage[] = [
    { id: 'pending', name: 'Pending', order: 0, color: '#f59e0b', wip_limit: null },
    { id: 'processing', name: 'Processing', order: 1, color: '#3b82f6', wip_limit: null },
    { id: 'qualified', name: 'Qualified', order: 2, color: '#22c55e', wip_limit: null },
    { id: 'enhanced', name: 'Enhanced', order: 3, color: '#a855f7', wip_limit: null },
    { id: 'low_score', name: 'Low Score', order: 4, color: '#ef4444', wip_limit: null },
    { id: 'error', name: 'Error', order: 5, color: '#ef4444', wip_limit: null },
    { id: 'skipped', name: 'Skipped', order: 6, color: '#64748b', wip_limit: null },
];

// === Utility types ===
export function getScoreClass(score: number | null): string {
    if (score === null) return '';
    if (score >= 90) return 'score--excellent';
    if (score >= 80) return 'score--great';
    if (score >= 70) return 'score--good';
    if (score >= 50) return 'score--partial';
    return 'score--weak';
}

export function getStatusLabel(status: JobStatus): string {
    const labels: Record<JobStatus, string> = {
        pending: 'Pending',
        processing: 'Processing',
        qualified: 'Qualified',
        enhanced: 'Enhanced',
        low_score: 'Low Score',
        error: 'Error',
        skipped: 'Skipped',
    };
    return labels[status] || status;
}

// === Score Breakdown types (7-section AI analysis) ===
export interface ScoreSection {
    dimension: string;
    score: number;
    weight: number;
    strong_points: string[];
    weak_points: string[];
    recommendations: string[];
}

export interface ScoreBreakdown {
    overall_score: number;
    interview_probability: 'HIGH' | 'MEDIUM' | 'LOW';
    sections: ScoreSection[];
    key_risks: string[];
    cv_enhancement_priorities: string[];
    model_used: string;
    scored_at: string;
}
