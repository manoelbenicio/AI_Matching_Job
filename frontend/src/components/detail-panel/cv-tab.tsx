'use client';

import { useState } from 'react';
import { useEnhanceCv, useCvVersions } from '@/hooks/use-cv';
import type { Job, CvEnhanceResponse, DiffChunk, CvVersion } from '@/lib/types';
import './cv-tab.css';

export function CvTab({ job }: { job: Job }) {
    const enhanceMutation = useEnhanceCv();
    const { data: versions, isLoading: versionsLoading } = useCvVersions(job.id);
    const [lastResult, setLastResult] = useState<CvEnhanceResponse | null>(null);
    const [selectedVersion, setSelectedVersion] = useState<CvVersion | null>(null);
    const [viewMode, setViewMode] = useState<'result' | 'diff' | 'history'>('result');

    const handleEnhance = async () => {
        const result = await enhanceMutation.mutateAsync({ job_id: job.id });
        setLastResult(result);
        setViewMode('result');
    };

    const isEnhancing = enhanceMutation.isPending;
    const hasVersions = versions && versions.length > 0;

    return (
        <div className="cv-tab">
            {/* Enhance action */}
            <div className="cv-tab__action">
                <button
                    className="cv-tab__enhance-btn"
                    onClick={handleEnhance}
                    disabled={isEnhancing}
                >
                    {isEnhancing ? (
                        <>
                            <span className="cv-tab__spinner" />
                            Analyzing with Gemini…
                        </>
                    ) : (
                        <>
                            <span className="cv-tab__icon">✨</span>
                            Enhance CV for this Role
                        </>
                    )}
                </button>
                <p className="cv-tab__hint">
                    Uses Gemini 2.0 Flash to tailor your resume for <strong>{job.job_title}</strong> at <strong>{job.company_name}</strong>
                </p>
            </div>

            {/* View toggle */}
            {(lastResult || hasVersions) && (
                <div className="cv-tab__toggle">
                    <button
                        className={`cv-tab__toggle-btn ${viewMode === 'result' ? 'cv-tab__toggle-btn--active' : ''}`}
                        onClick={() => setViewMode('result')}
                    >
                        📊 Results
                    </button>
                    <button
                        className={`cv-tab__toggle-btn ${viewMode === 'diff' ? 'cv-tab__toggle-btn--active' : ''}`}
                        onClick={() => setViewMode('diff')}
                    >
                        📝 Diff View
                    </button>
                    <button
                        className={`cv-tab__toggle-btn ${viewMode === 'history' ? 'cv-tab__toggle-btn--active' : ''}`}
                        onClick={() => setViewMode('history')}
                    >
                        🕐 History ({versions?.length || 0})
                    </button>
                </div>
            )}

            {/* Result view */}
            {viewMode === 'result' && lastResult && (
                <div className="cv-tab__result">
                    {/* Fit Score */}
                    <div className="cv-tab__score-card">
                        <div className="cv-tab__score-ring" data-score={lastResult.fit_score}>
                            <span className="cv-tab__score-value">{lastResult.fit_score}</span>
                            <span className="cv-tab__score-label">Fit Score</span>
                        </div>
                    </div>

                    {/* Skills */}
                    <div className="cv-tab__skills">
                        {lastResult.skills_matched.length > 0 && (
                            <div className="cv-tab__skill-group">
                                <h4 className="cv-tab__skill-title cv-tab__skill-title--matched">
                                    ✅ Skills Matched ({lastResult.skills_matched.length})
                                </h4>
                                <div className="cv-tab__skill-tags">
                                    {lastResult.skills_matched.map((s, i) => (
                                        <span key={i} className="cv-tab__skill-tag cv-tab__skill-tag--matched">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {lastResult.skills_missing.length > 0 && (
                            <div className="cv-tab__skill-group">
                                <h4 className="cv-tab__skill-title cv-tab__skill-title--missing">
                                    ⚠️ Skills Missing ({lastResult.skills_missing.length})
                                </h4>
                                <div className="cv-tab__skill-tags">
                                    {lastResult.skills_missing.map((s, i) => (
                                        <span key={i} className="cv-tab__skill-tag cv-tab__skill-tag--missing">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Enhanced CV */}
                    <div className="cv-tab__section">
                        <h4 className="cv-tab__section-title">Enhanced Resume</h4>
                        <pre className="cv-tab__preview">{lastResult.enhanced_cv}</pre>
                    </div>
                </div>
            )}

            {/* Diff view */}
            {viewMode === 'diff' && lastResult?.diff && (
                <DiffView chunks={lastResult.diff} />
            )}
            {viewMode === 'diff' && !lastResult?.diff && selectedVersion && (
                <div className="cv-tab__empty">
                    Select a version from history, then re-enhance to see the diff.
                </div>
            )}

            {/* History view */}
            {viewMode === 'history' && (
                <VersionHistory
                    versions={versions || []}
                    isLoading={versionsLoading}
                    selectedVersion={selectedVersion}
                    onSelect={setSelectedVersion}
                />
            )}

            {/* Empty state */}
            {!lastResult && !hasVersions && !isEnhancing && (
                <div className="cv-tab__empty-state">
                    <div className="cv-tab__empty-icon">🎯</div>
                    <h3>No CV analysis yet</h3>
                    <p>Click the button above to generate an AI-enhanced resume tailored to this role.</p>
                </div>
            )}
        </div>
    );
}


// ── Diff View Component ──

function DiffView({ chunks }: { chunks: DiffChunk[] }) {
    return (
        <div className="cv-diff">
            <div className="cv-diff__legend">
                <span className="cv-diff__legend-item cv-diff__legend-item--added">+ Added</span>
                <span className="cv-diff__legend-item cv-diff__legend-item--removed">− Removed</span>
                <span className="cv-diff__legend-item cv-diff__legend-item--unchanged">Unchanged</span>
            </div>
            <div className="cv-diff__content">
                {chunks.map((chunk, i) => (
                    <div
                        key={i}
                        className={`cv-diff__chunk cv-diff__chunk--${chunk.type}`}
                    >
                        <span className="cv-diff__marker">
                            {chunk.type === 'added' ? '+' : chunk.type === 'removed' ? '−' : ' '}
                        </span>
                        <span className="cv-diff__text">{chunk.content}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}


// ── Version History Component ──

function VersionHistory({
    versions,
    isLoading,
    selectedVersion,
    onSelect,
}: {
    versions: CvVersion[];
    isLoading: boolean;
    selectedVersion: CvVersion | null;
    onSelect: (v: CvVersion) => void;
}) {
    if (isLoading) {
        return (
            <div className="cv-history">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="skeleton" style={{ height: 60, marginBottom: 8, borderRadius: 8 }} />
                ))}
            </div>
        );
    }

    if (versions.length === 0) {
        return (
            <div className="cv-tab__empty">
                No versions yet. Enhance your CV to create the first version.
            </div>
        );
    }

    return (
        <div className="cv-history">
            <div className="cv-history__timeline">
                {versions.map((v) => (
                    <button
                        key={v.id}
                        className={`cv-history__item ${selectedVersion?.id === v.id ? 'cv-history__item--active' : ''}`}
                        onClick={() => onSelect(v)}
                    >
                        <div className="cv-history__dot" />
                        <div className="cv-history__info">
                            <div className="cv-history__header">
                                <span className="cv-history__version">v{v.version_number}</span>
                                {v.fit_score !== null && (
                                    <span className="cv-history__score">
                                        Score: {v.fit_score}
                                    </span>
                                )}
                            </div>
                            <span className="cv-history__date">
                                {new Date(v.created_at).toLocaleString()}
                            </span>
                            {v.skills_matched && v.skills_matched.length > 0 && (
                                <span className="cv-history__skills">
                                    {v.skills_matched.length} skills matched
                                </span>
                            )}
                        </div>
                    </button>
                ))}
            </div>

            {/* Preview selected version */}
            {selectedVersion && (
                <div className="cv-history__preview">
                    <h4 className="cv-tab__section-title">
                        Version {selectedVersion.version_number}
                        {selectedVersion.fit_score !== null && (
                            <span className="cv-history__preview-score"> — Score: {selectedVersion.fit_score}/100</span>
                        )}
                    </h4>
                    {selectedVersion.enhanced_content ? (
                        <pre className="cv-tab__preview">{selectedVersion.enhanced_content}</pre>
                    ) : (
                        <pre className="cv-tab__preview">{selectedVersion.content}</pre>
                    )}
                </div>
            )}
        </div>
    );
}
