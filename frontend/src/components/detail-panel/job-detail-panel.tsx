'use client';

import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import { useJob } from '@/hooks/use-jobs';
import { useAuditTrail } from '@/hooks/use-cv';
import { CvTab } from '@/components/cv/cv-tab';
import './job-detail-panel.css';

type TabId = 'details' | 'cv' | 'audit';

const TABS: { id: TabId; label: string }[] = [
    { id: 'details', label: 'Details' },
    { id: 'cv', label: 'CV Analysis' },
    { id: 'audit', label: 'Audit Trail' },
];

export function JobDetailPanel() {
    const selectedJobId = useAppStore((s) => s.selectedJobId);
    const setSelectedJobId = useAppStore((s) => s.setSelectedJobId);
    const panelRef = useRef<HTMLDivElement>(null);
    const [activeTab, setActiveTab] = useState<TabId>('details');

    const { data: job, isLoading } = useJob(selectedJobId);
    const { data: auditEvents, isLoading: auditLoading } = useAuditTrail(
        activeTab === 'audit' ? selectedJobId : null
    );

    // Reset tab when job changes
    useEffect(() => {
        setActiveTab('details');
    }, [selectedJobId]);

    // Close on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') setSelectedJobId(null);
        };
        if (selectedJobId) {
            document.addEventListener('keydown', handler);
            return () => document.removeEventListener('keydown', handler);
        }
    }, [selectedJobId, setSelectedJobId]);

    // Click outside to close
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
                setSelectedJobId(null);
            }
        };
        if (selectedJobId) {
            setTimeout(() => document.addEventListener('mousedown', handler), 100);
            return () => document.removeEventListener('mousedown', handler);
        }
    }, [selectedJobId, setSelectedJobId]);

    if (!selectedJobId) return null;

    const statusColor = (s: string) => {
        const map: Record<string, string> = {
            qualified: 'var(--color-success)',
            enhanced: 'var(--color-info)',
            pending: 'var(--color-warning)',
            processing: 'var(--color-accent)',
            low_score: 'var(--color-danger)',
            error: 'var(--color-danger)',
            skipped: 'var(--color-text-muted)',
        };
        return map[s] || 'var(--color-text-muted)';
    };

    const scoreColor = (score: number | null) => {
        if (score === null || score === undefined) return 'var(--color-text-muted)';
        if (score >= 80) return 'var(--color-success)';
        if (score >= 60) return 'var(--color-warning)';
        return 'var(--color-danger)';
    };

    return (
        <>
            <div className="detail-backdrop" onClick={() => setSelectedJobId(null)} />
            <div className="detail-panel" ref={panelRef}>
                {isLoading ? (
                    <div className="detail-panel__loading">
                        <div className="skeleton" style={{ width: '60%', height: 28 }} />
                        <div className="skeleton" style={{ width: '40%', height: 20, marginTop: 12 }} />
                        <div className="skeleton" style={{ width: '100%', height: 120, marginTop: 24 }} />
                    </div>
                ) : job ? (
                    <>
                        {/* Header */}
                        <div className="detail-panel__header">
                            <button
                                className="detail-panel__close"
                                onClick={() => setSelectedJobId(null)}
                                aria-label="Close panel"
                            >
                                ✕
                            </button>
                            <h2 className="detail-panel__title">{job.job_title}</h2>
                            <p className="detail-panel__company">{job.company_name}</p>
                            <div className="detail-panel__badges">
                                <span
                                    className="detail-panel__badge"
                                    style={{ borderColor: statusColor(job.status || '') }}
                                >
                                    {(job.status || 'unknown').replace('_', ' ')}
                                </span>
                                {job.score !== null && job.score !== undefined && (
                                    <span
                                        className="detail-panel__score"
                                        style={{ color: scoreColor(job.score) }}
                                    >
                                        {job.score}/100
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* Tab Bar */}
                        <div className="detail-panel__tabs">
                            {TABS.map((tab) => (
                                <button
                                    key={tab.id}
                                    className={`detail-panel__tab ${activeTab === tab.id ? 'detail-panel__tab--active' : ''}`}
                                    onClick={() => setActiveTab(tab.id)}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        {/* Tab Content */}
                        <div className="detail-panel__tab-content">
                            {activeTab === 'details' && (
                                <DetailsTab job={job} statusColor={statusColor} />
                            )}
                            {activeTab === 'cv' && (
                                <CvTab job={job} />
                            )}
                            {activeTab === 'audit' && (
                                <AuditTab events={auditEvents ?? []} loading={auditLoading} />
                            )}
                        </div>
                    </>
                ) : (
                    <div className="detail-panel__empty">Job not found</div>
                )}
            </div>
        </>
    );
}


// ── Details Tab (original panel content) ──────────────────────────────────

function DetailsTab({ job }: { job: import('@/lib/types').Job; statusColor: (s: string) => string }) {
    return (
        <>
            {/* Info grid */}
            <div className="detail-panel__grid">
                <InfoItem label="Location" value={job.location} />
                <InfoItem label="Work Type" value={job.work_type} />
                <InfoItem label="Seniority" value={job.seniority_level} />
                <InfoItem label="Employment" value={job.employment_type} />
                <InfoItem label="Salary" value={job.salary_info} />
                <InfoItem label="Sector" value={job.sector} />
            </div>

            {/* Justification */}
            {job.justification && (
                <div className="detail-panel__section">
                    <h3 className="detail-panel__section-title">AI Assessment</h3>
                    <p className="detail-panel__text">{job.justification}</p>
                </div>
            )}

            {/* Description */}
            {job.job_description && (
                <div className="detail-panel__section">
                    <h3 className="detail-panel__section-title">Job Description</h3>
                    <p className="detail-panel__text">{job.job_description}</p>
                </div>
            )}

            {/* Actions */}
            <div className="detail-panel__actions">
                {job.job_url && (
                    <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-primary"
                    >
                        View on LinkedIn
                    </a>
                )}
                {job.apply_url && (
                    <a
                        href={job.apply_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-outline"
                    >
                        Apply
                    </a>
                )}
            </div>

            {/* Error message */}
            {job.error_message && (
                <div className="detail-panel__error">
                    <strong>Error:</strong> {job.error_message}
                </div>
            )}
        </>
    );
}


// ── Audit Trail Tab ──────────────────────────────────────────────────────

function AuditTab({ events, loading }: { events: import('@/lib/types').AuditEvent[]; loading: boolean }) {
    if (loading) {
        return (
            <div className="cv-tab__loading">
                <div className="skeleton" style={{ width: '100%', height: 56 }} />
                <div className="skeleton" style={{ width: '100%', height: 56, marginTop: 8 }} />
                <div className="skeleton" style={{ width: '100%', height: 56, marginTop: 8 }} />
            </div>
        );
    }

    if (events.length === 0) {
        return (
            <div className="audit-trail__empty">
                No audit events recorded for this job yet.
            </div>
        );
    }

    return (
        <div className="audit-trail">
            {events.map((ev) => (
                <div key={ev.id} className="audit-trail__item">
                    <div className="audit-trail__dot" />
                    <div className="audit-trail__body">
                        <p className="audit-trail__action">{ev.action}</p>
                        {ev.field && (
                            <p className="audit-trail__field">Field: {ev.field}</p>
                        )}
                        {(ev.old_value || ev.new_value) && (
                            <div className="audit-trail__values">
                                {ev.old_value && (
                                    <span className="audit-trail__old">{ev.old_value}</span>
                                )}
                                {ev.old_value && ev.new_value && (
                                    <span className="audit-trail__arrow">→</span>
                                )}
                                {ev.new_value && (
                                    <span className="audit-trail__new">{ev.new_value}</span>
                                )}
                            </div>
                        )}
                        <p className="audit-trail__time">
                            {new Date(ev.created_at).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                                second: '2-digit',
                            })}
                        </p>
                    </div>
                </div>
            ))}
        </div>
    );
}


// ── Helpers ──────────────────────────────────────────────────────────────

function InfoItem({ label, value }: { label: string; value?: string | null }) {
    if (!value) return null;
    return (
        <div className="detail-panel__info-item">
            <span className="detail-panel__info-label">{label}</span>
            <span className="detail-panel__info-value">{value}</span>
        </div>
    );
}
