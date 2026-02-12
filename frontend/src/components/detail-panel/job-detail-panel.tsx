'use client';

import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import { SkeletonDetail } from '@/components/ui/skeleton';
import { useJob } from '@/hooks/use-jobs';
import { CvTab } from '../cv/cv-tab';
import { AuditTab } from './audit-tab';
import { ScoreBreakdownTab } from './score-breakdown-tab';
import './job-detail-panel.css';

type TabId = 'details' | 'score' | 'cv' | 'audit';

export function JobDetailPanel() {
    const selectedJobId = useAppStore((s) => s.selectedJobId);
    const setSelectedJobId = useAppStore((s) => s.setSelectedJobId);
    const panelRef = useRef<HTMLDivElement>(null);
    const [activeTab, setActiveTab] = useState<TabId>('details');

    const { data: job, isLoading } = useJob(selectedJobId);

    // Reset tab when a different job is selected
    useEffect(() => {
        if (selectedJobId) setActiveTab('details');
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

    const TABS: { id: TabId; label: string; icon: string }[] = [
        { id: 'details', label: 'Details', icon: '📋' },
        { id: 'score', label: 'Score', icon: '📊' },
        { id: 'cv', label: 'CV Analysis', icon: '🤖' },
        { id: 'audit', label: 'Activity', icon: '📜' },
    ];

    return (
        <>
            <div className="detail-backdrop" onClick={() => setSelectedJobId(null)} />
            <div className="detail-panel" ref={panelRef}>
                {isLoading ? (
                    <SkeletonDetail />
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
                                    <span className="detail-panel__tab-icon">{tab.icon}</span>
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        {/* Tab Content */}
                        <div className="detail-panel__tab-content" key={activeTab}>
                            {activeTab === 'details' && (
                                <DetailsTab job={job} statusColor={statusColor} />
                            )}
                            {activeTab === 'score' && (
                                <ScoreBreakdownTab breakdown={job.detailed_score} />
                            )}
                            {activeTab === 'cv' && (
                                <CvTab job={job} />
                            )}
                            {activeTab === 'audit' && (
                                <AuditTab jobId={job.id} />
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

// ── Details Tab (existing content, extracted) ────────────────────────────

function DetailsTab({ job, statusColor }: {
    job: import('@/lib/types').Job;
    statusColor: (s: string) => string;
}) {
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
                    <p className="detail-panel__text detail-panel__description">
                        {job.job_description}
                    </p>
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

function InfoItem({ label, value }: { label: string; value?: string | null }) {
    if (!value) return null;
    return (
        <div className="detail-panel__info-item">
            <span className="detail-panel__info-label">{label}</span>
            <span className="detail-panel__info-value">{value}</span>
        </div>
    );
}
