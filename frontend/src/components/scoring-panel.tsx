'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

// ── Types ────────────────────────────────────────────────────────────────

interface ScoredJob {
    type: 'scored' | 'error' | 'scoring';
    job_id: number;
    job_title: string;
    company: string;
    score?: number;
    justification?: string;
    skills_matched?: string[];
    skills_missing?: string[];
    model?: string;
    tokens_used?: number;
    elapsed_seconds?: number;
    prompt_preview?: string;
    raw_response?: string;
    error?: string;
    progress: number;
    total: number;
}

interface ScoringState {
    status: 'idle' | 'running' | 'complete' | 'cancelled' | 'error';
    scored: number;
    total: number;
    totalTokens: number;
    errors: number;
    results: ScoredJob[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// ── Score badge color ────────────────────────────────────────────────────

function getScoreColor(score: number): string {
    if (score >= 80) return 'var(--score-excellent)';
    if (score >= 65) return 'var(--score-great)';
    if (score >= 50) return 'var(--score-good)';
    if (score >= 30) return 'var(--score-partial)';
    return 'var(--score-weak)';
}

function getScoreLabel(score: number): string {
    if (score >= 80) return 'Excellent';
    if (score >= 65) return 'Great';
    if (score >= 50) return 'Good';
    if (score >= 30) return 'Partial';
    return 'Weak';
}

// ── Icons ────────────────────────────────────────────────────────────────

const CloseIcon = () => (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <line x1="4" y1="4" x2="12" y2="12" />
        <line x1="12" y1="4" x2="4" y2="12" />
    </svg>
);

const PlayIcon = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path d="M4 2.5v11l10-5.5L4 2.5z" />
    </svg>
);

const StopIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
        <rect x="3" y="3" width="10" height="10" rx="1.5" />
    </svg>
);

const CheckIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="3 8 6.5 11.5 13 4" />
    </svg>
);

const ErrorIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="8" cy="8" r="6" />
        <line x1="8" y1="5" x2="8" y2="9" />
        <circle cx="8" cy="11.5" r="0.5" fill="currentColor" />
    </svg>
);

const SpinnerIcon = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" className="scoring-spinner">
        <path d="M8 2a6 6 0 0 1 6 6" strokeLinecap="round" />
    </svg>
);

const ChevronIcon = ({ expanded }: { expanded: boolean }) => (
    <svg
        width="12" height="12" viewBox="0 0 16 16"
        fill="none" stroke="currentColor" strokeWidth="2"
        style={{ transform: expanded ? 'rotate(90deg)' : 'rotate(0)', transition: 'transform 0.2s' }}
    >
        <polyline points="6 4 10 8 6 12" />
    </svg>
);

// ── Main Component ───────────────────────────────────────────────────────

export function ScoringPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
    const [batchSize, setBatchSize] = useState(25);
    const [statusFilter, setStatusFilter] = useState('Pending');
    const [sortBy, setSortBy] = useState('newest_first');
    const [unscoredCount, setUnscoredCount] = useState<number | null>(null);
    const [state, setState] = useState<ScoringState>({
        status: 'idle',
        scored: 0,
        total: 0,
        totalTokens: 0,
        errors: 0,
        results: [],
    });
    const [expandedId, setExpandedId] = useState<number | null>(null);
    const feedRef = useRef<HTMLDivElement>(null);
    const eventSourceRef = useRef<EventSource | null>(null);

    // Fetch unscored count on open
    useEffect(() => {
        if (open) {
            fetch(`${API_BASE}/scoring/unscored-count?status=${statusFilter}`)
                .then(r => r.json())
                .then(data => setUnscoredCount(data.count))
                .catch(() => setUnscoredCount(null));
        }
    }, [open, statusFilter]);

    // Auto-scroll feed
    useEffect(() => {
        if (feedRef.current) {
            feedRef.current.scrollTop = feedRef.current.scrollHeight;
        }
    }, [state.results]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            eventSourceRef.current?.close();
        };
    }, []);

    const startScoring = useCallback(() => {
        setState({
            status: 'running',
            scored: 0,
            total: 0,
            totalTokens: 0,
            errors: 0,
            results: [],
        });

        // Use fetch with reader for POST SSE (EventSource only supports GET)
        const controller = new AbortController();

        fetch(`${API_BASE}/scoring/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_size: batchSize, status_filter: statusFilter, sort_by: sortBy }),
            signal: controller.signal,
        })
            .then(async response => {
                if (!response.body) throw new Error('No response body');
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    let eventType = '';
                    let eventData = '';

                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7).trim();
                        } else if (line.startsWith('data: ')) {
                            eventData = line.slice(6).trim();
                        } else if (line === '' && eventData) {
                            try {
                                const data = JSON.parse(eventData);
                                handleSSEEvent(eventType, data);
                            } catch {
                                // skip malformed
                            }
                            eventType = '';
                            eventData = '';
                        }
                    }
                }

                // Stream ended — mark complete if still running
                setState(prev => {
                    if (prev.status === 'running') {
                        return { ...prev, status: 'complete' };
                    }
                    return prev;
                });
            })
            .catch(err => {
                if (err.name !== 'AbortError') {
                    setState(prev => ({
                        ...prev,
                        status: 'error',
                        results: [...prev.results, {
                            type: 'error',
                            job_id: 0,
                            job_title: 'Connection Error',
                            company: '',
                            error: err.message,
                            progress: prev.scored,
                            total: prev.total,
                        }],
                    }));
                }
            });

        // Store abort controller
        (eventSourceRef as any).current = { close: () => controller.abort() };
    }, [batchSize, statusFilter]);

    const handleSSEEvent = useCallback((eventType: string, data: any) => {
        switch (eventType) {
            case 'start':
                setState(prev => ({ ...prev, total: data.total }));
                break;
            case 'scoring':
                setState(prev => ({
                    ...prev,
                    results: [...prev.results, {
                        type: 'scoring',
                        job_id: data.job_id,
                        job_title: data.job_title,
                        company: data.company,
                        progress: data.progress,
                        total: data.total,
                    }],
                }));
                break;
            case 'scored':
                setState(prev => ({
                    ...prev,
                    scored: data.progress,
                    total: data.total,
                    totalTokens: prev.totalTokens + (data.tokens_used || 0),
                    // Replace the "scoring" entry with the "scored" entry
                    results: [
                        ...prev.results.filter(r => !(r.type === 'scoring' && r.job_id === data.job_id)),
                        { ...data, type: 'scored' },
                    ],
                }));
                break;
            case 'error':
                if (data.job_id) {
                    setState(prev => ({
                        ...prev,
                        scored: data.progress || prev.scored,
                        errors: prev.errors + 1,
                        results: [
                            ...prev.results.filter(r => !(r.type === 'scoring' && r.job_id === data.job_id)),
                            { ...data, type: 'error' },
                        ],
                    }));
                }
                break;
            case 'cancelled':
                setState(prev => ({ ...prev, status: 'cancelled', scored: data.scored }));
                break;
            case 'complete':
                setState(prev => ({
                    ...prev,
                    status: 'complete',
                    scored: data.scored,
                    errors: data.errors,
                    totalTokens: data.total_tokens || prev.totalTokens,
                }));
                break;
            case 'info':
                setState(prev => ({
                    ...prev,
                    status: 'complete',
                    results: [...prev.results, {
                        type: 'error',
                        job_id: 0,
                        job_title: 'Info',
                        company: '',
                        error: data.message,
                        progress: 0,
                        total: 0,
                    }],
                }));
                break;
        }
    }, []);

    const stopScoring = useCallback(() => {
        fetch(`${API_BASE}/scoring/stop`, { method: 'POST' })
            .catch(() => { });
        eventSourceRef.current?.close();
    }, []);

    const progressPct = state.total > 0 ? Math.round((state.scored / state.total) * 100) : 0;

    if (!open) return null;

    return (
        <div className="scoring-overlay" onClick={onClose}>
            <div className="scoring-panel" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="scoring-panel__header">
                    <div className="scoring-panel__title">
                        <svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="var(--accent-primary)" strokeWidth="1.5">
                            <path d="M8 1l2 3h3l-2.5 3L12 11l-4-2-4 2 1.5-4L3 4h3L8 1z" />
                        </svg>
                        <h2>AI Scoring Pipeline</h2>
                    </div>
                    <button className="scoring-panel__close" onClick={onClose}>
                        <CloseIcon />
                    </button>
                </div>

                {/* Controls */}
                <div className="scoring-panel__controls">
                    <div className="scoring-control-row">
                        <div className="scoring-control-group">
                            <label className="scoring-label">Batch Size</label>
                            <select
                                className="scoring-select"
                                value={batchSize}
                                onChange={e => setBatchSize(Number(e.target.value))}
                                disabled={state.status === 'running'}
                            >
                                <option value={5}>5 jobs</option>
                                <option value={10}>10 jobs</option>
                                <option value={25}>25 jobs</option>
                                <option value={50}>50 jobs</option>
                                <option value={100}>100 jobs</option>
                            </select>
                        </div>
                        <div className="scoring-control-group">
                            <label className="scoring-label">Filter</label>
                            <select
                                className="scoring-select"
                                value={statusFilter}
                                onChange={e => setStatusFilter(e.target.value)}
                                disabled={state.status === 'running'}
                            >
                                <option value="Pending">Pending only</option>
                                <option value="Applied">Applied</option>
                                <option value="Interview">Interview</option>
                            </select>
                        </div>
                        <div className="scoring-control-group">
                            <label className="scoring-label">Order</label>
                            <select
                                className="scoring-select"
                                value={sortBy}
                                onChange={e => setSortBy(e.target.value)}
                                disabled={state.status === 'running'}
                            >
                                <option value="newest_first">Newest First</option>
                                <option value="oldest_first">Oldest First</option>
                                <option value="id">Job ID</option>
                            </select>
                        </div>
                        <div className="scoring-control-group scoring-control-group--info">
                            <span className="scoring-unscored-badge">
                                {unscoredCount !== null ? `${unscoredCount} unscored` : '…'}
                            </span>
                        </div>
                    </div>

                    <div className="scoring-actions">
                        {state.status !== 'running' ? (
                            <button className="btn scoring-btn scoring-btn--start" onClick={startScoring}>
                                <PlayIcon />
                                <span>Start Scoring</span>
                            </button>
                        ) : (
                            <button className="btn scoring-btn scoring-btn--stop" onClick={stopScoring}>
                                <StopIcon />
                                <span>Stop</span>
                            </button>
                        )}
                    </div>
                </div>

                {/* Progress bar */}
                {(state.status === 'running' || state.status === 'complete' || state.status === 'cancelled') && (
                    <div className="scoring-progress">
                        <div className="scoring-progress__bar">
                            <div
                                className={`scoring-progress__fill ${state.status === 'complete' ? 'scoring-progress__fill--done' : ''}`}
                                style={{ width: `${progressPct}%` }}
                            />
                        </div>
                        <div className="scoring-progress__stats">
                            <span>
                                {state.status === 'running' && <SpinnerIcon />}
                                {state.status === 'complete' && <CheckIcon />}
                                {state.scored}/{state.total} scored
                            </span>
                            <span>{state.totalTokens.toLocaleString()} tokens</span>
                            {state.errors > 0 && (
                                <span className="scoring-progress__errors">
                                    <ErrorIcon /> {state.errors} errors
                                </span>
                            )}
                            <span className="scoring-progress__pct">{progressPct}%</span>
                        </div>
                    </div>
                )}

                {/* Live Feed */}
                <div className="scoring-feed" ref={feedRef}>
                    {state.results.length === 0 && state.status === 'idle' && (
                        <div className="scoring-feed__empty">
                            <svg width="48" height="48" viewBox="0 0 16 16" fill="none" stroke="var(--text-muted)" strokeWidth="0.8" opacity="0.5">
                                <path d="M8 1l2 3h3l-2.5 3L12 11l-4-2-4 2 1.5-4L3 4h3L8 1z" />
                            </svg>
                            <p>Configure batch size and click <strong>Start Scoring</strong> to begin</p>
                            <p className="scoring-feed__subtitle">Each job will be scored against the candidate resume using GPT-4o-mini</p>
                        </div>
                    )}

                    {state.results.map((item, idx) => (
                        <div
                            key={`${item.job_id}-${idx}`}
                            className={`scoring-feed__item scoring-feed__item--${item.type}`}
                        >
                            <div className="scoring-feed__item-main" onClick={() => item.type === 'scored' && setExpandedId(expandedId === item.job_id ? null : item.job_id)}>
                                <div className="scoring-feed__item-icon">
                                    {item.type === 'scoring' && <SpinnerIcon />}
                                    {item.type === 'scored' && <CheckIcon />}
                                    {item.type === 'error' && <ErrorIcon />}
                                </div>
                                <div className="scoring-feed__item-info">
                                    <span className="scoring-feed__item-title">{item.job_title}</span>
                                    {item.company && <span className="scoring-feed__item-company">{item.company}</span>}
                                </div>
                                {item.type === 'scored' && item.score !== undefined && (
                                    <div className="scoring-feed__item-score" style={{ '--score-color': getScoreColor(item.score) } as React.CSSProperties}>
                                        <span className="scoring-feed__score-value">{item.score}</span>
                                        <span className="scoring-feed__score-label">{getScoreLabel(item.score)}</span>
                                    </div>
                                )}
                                {item.type === 'error' && (
                                    <span className="scoring-feed__item-error-badge">Error</span>
                                )}
                                {item.type === 'scored' && (
                                    <ChevronIcon expanded={expandedId === item.job_id} />
                                )}
                            </div>

                            {/* Expanded details */}
                            {item.type === 'scored' && expandedId === item.job_id && (
                                <div className="scoring-feed__detail">
                                    <div className="scoring-feed__detail-section">
                                        <h4>Justification</h4>
                                        <p>{item.justification}</p>
                                    </div>
                                    {item.skills_matched && item.skills_matched.length > 0 && (
                                        <div className="scoring-feed__detail-section">
                                            <h4>Skills Matched</h4>
                                            <div className="scoring-feed__tags">
                                                {item.skills_matched.map(s => (
                                                    <span key={s} className="scoring-feed__tag scoring-feed__tag--match">{s}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {item.skills_missing && item.skills_missing.length > 0 && (
                                        <div className="scoring-feed__detail-section">
                                            <h4>Skills Missing</h4>
                                            <div className="scoring-feed__tags">
                                                {item.skills_missing.map(s => (
                                                    <span key={s} className="scoring-feed__tag scoring-feed__tag--miss">{s}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    <div className="scoring-feed__detail-meta">
                                        <span>Model: {item.model}</span>
                                        <span>{item.tokens_used} tokens</span>
                                        <span>{item.elapsed_seconds}s</span>
                                    </div>
                                </div>
                            )}

                            {item.type === 'error' && item.error && (
                                <div className="scoring-feed__detail scoring-feed__detail--error">
                                    <p>{item.error}</p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Summary footer */}
                {state.status === 'complete' && state.scored > 0 && (
                    <div className="scoring-panel__footer">
                        <span>✅ Scored {state.scored} jobs</span>
                        <span>{state.totalTokens.toLocaleString()} total tokens</span>
                        {state.errors > 0 && <span className="scoring-progress__errors">{state.errors} errors</span>}
                        <button className="btn btn--ghost btn--sm" onClick={onClose}>Done</button>
                    </div>
                )}
            </div>
        </div>
    );
}
