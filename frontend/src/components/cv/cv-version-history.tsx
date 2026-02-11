'use client';

import type { CvVersion } from '@/lib/types';

interface CvVersionHistoryProps {
    versions: CvVersion[];
    selectedId: number | null;
    onSelect: (version: CvVersion) => void;
}

export function CvVersionHistory({ versions, selectedId, onSelect }: CvVersionHistoryProps) {
    return (
        <div className="cv-history">
            {versions.map((v) => (
                <button
                    key={v.id}
                    className={`cv-history__item ${selectedId === v.id ? 'cv-history__item--active' : ''}`}
                    onClick={() => onSelect(v)}
                >
                    <div className="cv-history__row">
                        <span className="cv-history__version">v{v.version_number}</span>
                        <span className="cv-history__date">
                            {new Date(v.created_at).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                            })}
                        </span>
                    </div>
                    <div className="cv-history__meta">
                        {v.fit_score !== null && (
                            <span className="cv-history__score" data-level={getScoreLevel(v.fit_score)}>
                                {v.fit_score}/100
                            </span>
                        )}
                        <span className="cv-history__skills">
                            {v.skills_matched.length} matched · {v.skills_missing.length} missing
                        </span>
                    </div>
                </button>
            ))}
        </div>
    );
}

function getScoreLevel(score: number): string {
    if (score >= 90) return 'excellent';
    if (score >= 80) return 'great';
    if (score >= 70) return 'good';
    if (score >= 50) return 'partial';
    return 'weak';
}
