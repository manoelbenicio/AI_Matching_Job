'use client';

import { useState, useRef } from 'react';
import { api } from '@/lib/api';
import { useAppStore } from '@/stores/app-store';

// ── Icons ────────────────────────────────────────────────────────────────
const LinkIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M6.7 9.3a3.3 3.3 0 0 0 4.7 0l2-2a3.3 3.3 0 0 0-4.7-4.7l-1 1" />
        <path d="M9.3 6.7a3.3 3.3 0 0 0-4.7 0l-2 2a3.3 3.3 0 0 0 4.7 4.7l1-1" />
    </svg>
);

const SpinnerSmall = () => (
    <svg className="settings-spinner" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M8 1a7 7 0 1 0 7 7" />
    </svg>
);

const CheckCircle = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--green-500, #22c55e)" strokeWidth="1.5">
        <circle cx="8" cy="8" r="7" />
        <polyline points="5,8 7,10.5 11,5.5" />
    </svg>
);

const ErrorCircle = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--red-500, #ef4444)" strokeWidth="1.5">
        <circle cx="8" cy="8" r="7" />
        <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" />
    </svg>
);

// ── Score color helper ──────────────────────────────────────────────────
function getScoreColor(score: number): string {
    if (score >= 70) return 'var(--green-500, #22c55e)';
    if (score >= 50) return 'var(--yellow-500, #eab308)';
    return 'var(--red-500, #ef4444)';
}

function getInterviewBadge(prob: string): { color: string; label: string } {
    switch (prob) {
        case 'HIGH': return { color: '#22c55e', label: '🟢 HIGH' };
        case 'MEDIUM': return { color: '#eab308', label: '🟡 MEDIUM' };
        default: return { color: '#ef4444', label: '🔴 LOW' };
    }
}

// ── Types ────────────────────────────────────────────────────────────────
type FetchState = 'idle' | 'fetching' | 'fetched' | 'scoring' | 'scored' | 'error';

interface SectionScore {
    dimension: string;
    score: number;
    strong: string[];
    weak: string[];
    recommendations: string[];
}

interface ScoreResult {
    overall_score: number;
    overall_justification: string;
    sections: SectionScore[];
    skills_matched: string[];
    skills_missing: string[];
    interview_probability: string;
    key_risks: string[];
    cv_enhancement_priority: string[];
}

interface JobData {
    id: number;
    job_title?: string;
    company_name?: string;
    location?: string;
    employment_type?: string;
    seniority_level?: string;
    salary_info?: string;
    job_description?: string;
    score?: number;
}

// ── Component ────────────────────────────────────────────────────────────
export function QuickAddBar({ open, onClose }: { open: boolean; onClose: () => void }) {
    const [url, setUrl] = useState('');
    const [state, setState] = useState<FetchState>('idle');
    const [job, setJob] = useState<JobData | null>(null);
    const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    if (!open) return null;

    const isValidUrl = url.trim().length > 10 && (url.includes('.') || url.includes('://'));

    const handleFetch = async () => {
        if (!url.trim()) return;
        setState('fetching');
        setError(null);
        setJob(null);
        setScoreResult(null);
        try {
            const resp = await api.fetchJobFromUrl(url.trim());
            if (resp.success && resp.job) {
                setJob(resp.job as unknown as JobData);
                setState('fetched');
            } else {
                setState('error');
                setError('Failed to fetch job data from URL');
            }
        } catch (e: any) {
            setState('error');
            const detail = typeof e?.body === 'object' ? e.body?.detail : String(e?.body || 'Could not fetch job data');
            setError(detail);
        }
    };

    const handleScore = async () => {
        if (!job) return;
        setState('scoring');
        setError(null);
        try {
            const resp = await api.scoreSingleJob(job.id);
            if (resp.success && resp.result) {
                const r = resp.result as unknown as ScoreResult;
                setScoreResult(r);
                setJob({ ...job, score: r.overall_score });
                setState('scored');
            } else {
                setState('error');
                setError('Scoring failed');
            }
        } catch (e: any) {
            setState('error');
            const detail = typeof e?.body === 'object' ? e.body?.detail : String(e?.body || 'Scoring failed');
            setError(detail);
        }
    };

    const handleReset = () => {
        setUrl('');
        setState('idle');
        setJob(null);
        setScoreResult(null);
        setError(null);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && isValidUrl) handleFetch();
        if (e.key === 'Escape') onClose();
    };

    return (
        <div className="quick-add-bar">
            <div className="quick-add-bar__content">
                {/* URL Input */}
                <div className="quick-add-bar__input-group">
                    <LinkIcon />
                    <input
                        ref={inputRef}
                        className="quick-add-bar__input"
                        type="url"
                        placeholder="Paste any job URL… (LinkedIn, Indeed, Glassdoor, etc.)"
                        value={url}
                        onChange={e => { setUrl(e.target.value); if (state === 'error') { setState('idle'); setError(null); } }}
                        onKeyDown={handleKeyDown}
                        autoFocus
                        disabled={state === 'fetching' || state === 'scoring'}
                    />
                    {state === 'idle' && (
                        <button
                            className="btn btn--primary btn--sm"
                            onClick={handleFetch}
                            disabled={!isValidUrl}
                        >
                            Fetch Job
                        </button>
                    )}
                    {state === 'fetching' && (
                        <button className="btn btn--primary btn--sm" disabled>
                            <SpinnerSmall /> Scraping…
                        </button>
                    )}
                    {state === 'fetched' && (
                        <button className="btn btn--primary btn--sm" onClick={handleScore}>
                            🎯 Score CV
                        </button>
                    )}
                    {state === 'scoring' && (
                        <button className="btn btn--primary btn--sm" disabled>
                            <SpinnerSmall /> Analyzing…
                        </button>
                    )}
                    {(state === 'scored' || state === 'error') && (
                        <button className="btn btn--ghost btn--sm" onClick={handleReset}>
                            New
                        </button>
                    )}
                    <button className="btn btn--ghost btn--sm quick-add-bar__close" onClick={onClose} title="Close">
                        ✕
                    </button>
                </div>

                {/* Error */}
                {state === 'error' && error && (
                    <div className="quick-add-result quick-add-result--error">
                        <ErrorCircle />
                        <span>{error}</span>
                    </div>
                )}

                {/* Job fetched — show summary */}
                {job && state !== 'idle' && state !== 'error' && (
                    <div className="quick-add-result quick-add-result--success">
                        <CheckCircle />
                        <div style={{ flex: 1 }}>
                            <strong>{job.job_title}</strong> at {job.company_name}
                            <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '2px' }}>
                                {[job.location, job.employment_type, job.seniority_level, job.salary_info]
                                    .filter(Boolean).join(' • ')}
                            </div>
                        </div>
                        {job.score != null && (
                            <span style={{
                                fontWeight: 700,
                                fontSize: '1.1rem',
                                color: getScoreColor(job.score),
                            }}>
                                {job.score}%
                            </span>
                        )}
                    </div>
                )}

                {/* Description preview + action links */}
                {job && state === 'fetched' && (
                    <div className="quick-add-result quick-add-result--preview">
                        {job.job_description && (
                            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                                {job.job_description.length > 200
                                    ? job.job_description.slice(0, 200) + '…'
                                    : job.job_description}
                            </p>
                        )}
                        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                            <button
                                className="btn btn--ghost btn--sm"
                                onClick={() => {
                                    useAppStore.getState().setSelectedJobId(job.id);
                                    onClose();
                                }}
                            >
                                📋 View Details
                            </button>
                            <a
                                className="btn btn--ghost btn--sm"
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ textDecoration: 'none' }}
                            >
                                🔗 Open Listing
                            </a>
                        </div>
                    </div>
                )}

                {/* Detailed scoring breakdown */}
                {scoreResult && state === 'scored' && (
                    <div className="quick-add-score-detail">
                        {/* Overall summary */}
                        <div className="quick-add-score-detail__header">
                            <div className="quick-add-score-detail__overall">
                                <span className="quick-add-score-detail__big-score" style={{ color: getScoreColor(scoreResult.overall_score) }}>
                                    {scoreResult.overall_score}%
                                </span>
                                <span className="quick-add-score-detail__badge" style={{
                                    color: getInterviewBadge(scoreResult.interview_probability).color
                                }}>
                                    Interview: {getInterviewBadge(scoreResult.interview_probability).label}
                                </span>
                            </div>
                            <p className="quick-add-score-detail__justification">{scoreResult.overall_justification}</p>
                        </div>

                        {/* Section scores */}
                        <div className="quick-add-score-detail__sections">
                            {scoreResult.sections.map((s, i) => (
                                <details key={i} className="quick-add-score-detail__section">
                                    <summary>
                                        <span className="quick-add-score-detail__dim">{s.dimension}</span>
                                        <span className="quick-add-score-detail__dim-score" style={{ color: getScoreColor(s.score) }}>
                                            {s.score}%
                                        </span>
                                    </summary>
                                    <div className="quick-add-score-detail__body">
                                        {s.strong.length > 0 && (
                                            <div className="quick-add-score-detail__block quick-add-score-detail__block--strong">
                                                <span className="quick-add-score-detail__label">✅ Strong</span>
                                                <ul>{s.strong.map((x, j) => <li key={j}>{x}</li>)}</ul>
                                            </div>
                                        )}
                                        {s.weak.length > 0 && (
                                            <div className="quick-add-score-detail__block quick-add-score-detail__block--weak">
                                                <span className="quick-add-score-detail__label">⚠️ Gaps</span>
                                                <ul>{s.weak.map((x, j) => <li key={j}>{x}</li>)}</ul>
                                            </div>
                                        )}
                                        {s.recommendations.length > 0 && (
                                            <div className="quick-add-score-detail__block quick-add-score-detail__block--recs">
                                                <span className="quick-add-score-detail__label">💡 Actions</span>
                                                <ul>{s.recommendations.map((x, j) => <li key={j}>{x}</li>)}</ul>
                                            </div>
                                        )}
                                    </div>
                                </details>
                            ))}
                        </div>

                        {/* Skills overview */}
                        <div className="quick-add-score-detail__skills">
                            {scoreResult.skills_matched.length > 0 && (
                                <div>
                                    <span className="quick-add-score-detail__label">✅ Matched Skills</span>
                                    <div className="quick-add-score-detail__tags">
                                        {scoreResult.skills_matched.map((s, i) => (
                                            <span key={i} className="quick-add-score-detail__tag quick-add-score-detail__tag--match">{s}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {scoreResult.skills_missing.length > 0 && (
                                <div>
                                    <span className="quick-add-score-detail__label">❌ Missing Skills</span>
                                    <div className="quick-add-score-detail__tags">
                                        {scoreResult.skills_missing.map((s, i) => (
                                            <span key={i} className="quick-add-score-detail__tag quick-add-score-detail__tag--miss">{s}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Enhancement priority + risks */}
                        {scoreResult.key_risks.length > 0 && (
                            <div className="quick-add-score-detail__risks">
                                <span className="quick-add-score-detail__label">🚨 Key Risks</span>
                                <ul>{scoreResult.key_risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
                            </div>
                        )}

                        {/* If score >= 70%, show enhance button */}
                        {scoreResult.overall_score >= 70 && (
                            <div className="quick-add-score-detail__actions">
                                <button className="btn btn--primary" style={{ width: '100%' }}>
                                    🚀 Enhance CV for This Job
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
