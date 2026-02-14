'use client';

import { useState } from 'react';
import type { ScoreBreakdown, ScoreSection } from '@/lib/types';
import './score-breakdown-tab.css';

// ── Helpers ──────────────────────────────────────────────────────────────

function sectionColor(score: number): string {
    if (score >= 80) return 'var(--score-excellent, #22c55e)';
    if (score >= 65) return 'var(--score-great, #34d399)';
    if (score >= 50) return 'var(--score-good, #3b82f6)';
    if (score >= 30) return 'var(--score-partial, #f59e0b)';
    return 'var(--score-weak, #ef4444)';
}

function heroGradient(score: number): string {
    if (score >= 80) return 'linear-gradient(135deg, #22c55e, #16a34a)';
    if (score >= 65) return 'linear-gradient(135deg, #34d399, #059669)';
    if (score >= 50) return 'linear-gradient(135deg, #3b82f6, #2563eb)';
    if (score >= 30) return 'linear-gradient(135deg, #f59e0b, #d97706)';
    return 'linear-gradient(135deg, #ef4444, #dc2626)';
}

// ── Component ────────────────────────────────────────────────────────────

interface Props {
    breakdown: ScoreBreakdown | null;
}

function pickList(primary?: string[], fallback?: string[]): string[] {
    if (Array.isArray(primary)) return primary;
    if (Array.isArray(fallback)) return fallback;
    return [];
}

export function ScoreBreakdownTab({ breakdown }: Props) {
    const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

    if (!breakdown) {
        return (
            <div className="score-breakdown__empty">
                <svg width="40" height="40" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3">
                    <path d="M8 1l2 3h3l-2.5 3L12 11l-4-2-4 2 1.5-4L3 4h3L8 1z" />
                </svg>
                <p>No detailed score breakdown yet. Run the AI scoring pipeline to generate an 8-dimension analysis.</p>
            </div>
        );
    }

    const toggleSection = (idx: number) =>
        setExpandedIdx(expandedIdx === idx ? null : idx);

    const modelLabel = breakdown.model_used
        || (breakdown.provider && breakdown.model ? `${breakdown.provider.toUpperCase()} (${breakdown.model})` : '')
        || breakdown.model
        || breakdown.provider
        || 'Unknown';
    const keyRisks = breakdown.key_risks ?? [];
    const priorities = breakdown.cv_enhancement_priority ?? breakdown.cv_enhancement_priorities ?? [];
    const interviewProbability: string =
        String(breakdown.interview_probability ?? breakdown.interview_probability_model ?? '').toUpperCase() || 'N/A';
    const fitLabel = breakdown.fit_assessment_label || '';
    const gapAnalysis = breakdown.gap_analysis;

    return (
        <div className="score-breakdown">
            {/* ── Hero card ──────────────────────────────────────── */}
            <div className="score-breakdown__hero">
                <div
                    className="score-breakdown__hero-score"
                    style={{ background: heroGradient(breakdown.overall_score) }}
                >
                    {breakdown.overall_score}
                    <span className="score-breakdown__hero-label">Score</span>
                </div>
                <div className="score-breakdown__hero-info">
                    <h3>Overall Match</h3>
                    <p>{modelLabel} • {breakdown.sections.length} dimensions</p>
                </div>
                <div className="score-breakdown__fit-assessment">
                    <span
                        className={`score-breakdown__interview-badge score-breakdown__interview-badge--${interviewProbability}`}
                    >
                        {interviewProbability === 'HIGH' && '🟢'}
                        {interviewProbability === 'MEDIUM' && '🟡'}
                        {interviewProbability === 'LOW' && '🔴'}
                        {interviewProbability} Chance
                    </span>
                    {fitLabel && (
                        <span className="score-breakdown__fit-label">{fitLabel}</span>
                    )}
                </div>
            </div>

            {breakdown.overall_justification && (
                <div className="score-breakdown__justification">
                    <p>{breakdown.overall_justification}</p>
                </div>
            )}

            {/* ── Section bars ───────────────────────────────────── */}
            {breakdown.sections.map((sec: ScoreSection, idx: number) => (
                <div key={idx} className="score-section">
                    <div className="score-section__header" onClick={() => toggleSection(idx)}>
                        <span className="score-section__dim">{sec.dimension}</span>
                        <div className="score-section__bar-track">
                            <div
                                className="score-section__bar-fill"
                                style={{
                                    width: `${sec.score}%`,
                                    background: sectionColor(sec.score),
                                }}
                            />
                        </div>
                        <span className="score-section__pct" style={{ color: sectionColor(sec.score) }}>
                            {sec.score}
                        </span>
                        {typeof sec.weight === 'number' && (
                            <span className="score-section__weight">{Math.round(sec.weight * 100)}%</span>
                        )}
                        <svg
                            className={`score-section__chevron ${expandedIdx === idx ? 'score-section__chevron--expanded' : ''}`}
                            width="10" height="10" viewBox="0 0 16 16"
                            fill="none" stroke="currentColor" strokeWidth="2"
                        >
                            <polyline points="6 4 10 8 6 12" />
                        </svg>
                    </div>

                    {expandedIdx === idx && (
                        <div className="score-section__body">
                            {pickList(sec.strong, sec.strong_points).length > 0 && (
                                <>
                                    <h5>Strengths</h5>
                                    <div className="score-section__items">
                                        {pickList(sec.strong, sec.strong_points).map((p, i) => (
                                            <div key={i} className="score-section__item score-section__item--strong">{p}</div>
                                        ))}
                                    </div>
                                </>
                            )}
                            {pickList(sec.weak, sec.weak_points).length > 0 && (
                                <>
                                    <h5>Weaknesses</h5>
                                    <div className="score-section__items">
                                        {pickList(sec.weak, sec.weak_points).map((p, i) => (
                                            <div key={i} className="score-section__item score-section__item--weak">{p}</div>
                                        ))}
                                    </div>
                                </>
                            )}
                            {(sec.recommendations ?? []).length > 0 && (
                                <>
                                    <h5>Recommendations</h5>
                                    <div className="score-section__items">
                                        {(sec.recommendations ?? []).map((p, i) => (
                                            <div key={i} className="score-section__item score-section__item--rec">{p}</div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            ))}

            {/* ── Key risks ─────────────────────────────────────── */}
            {keyRisks.length > 0 && (
                <div className="score-breakdown__meta">
                    <h4>⚠️ Key Risks</h4>
                    <div className="score-breakdown__tag-list">
                        {keyRisks.map((r, i) => (
                            <span key={i} className="score-breakdown__tag score-breakdown__tag--risk">{r}</span>
                        ))}
                    </div>
                </div>
            )}

            {/* ── CV Enhancement priorities ─────────────────────── */}
            {priorities.length > 0 && (
                <div className="score-breakdown__meta">
                    <h4>🎯 CV Enhancement Priorities</h4>
                    <div className="score-breakdown__tag-list">
                        {priorities.map((p, i) => (
                            <span key={i} className="score-breakdown__tag score-breakdown__tag--priority">{p}</span>
                        ))}
                    </div>
                </div>
            )}

            {gapAnalysis && gapAnalysis.gap_breakdown && gapAnalysis.gap_breakdown.length > 0 && (
                <div className="score-breakdown__meta score-breakdown__gap-analysis">
                    <h4>📊 Gap Analysis — {gapAnalysis.total_gap_percentage ?? (100 - breakdown.overall_score)} points to close</h4>
                    <div className="score-breakdown__gap-list">
                        {gapAnalysis.gap_breakdown.map((gap, i) => (
                            <div key={i} className="score-breakdown__gap-item">
                                <div className="score-breakdown__gap-header">
                                    <span className="score-breakdown__gap-category">{gap.category}</span>
                                    <span className="score-breakdown__gap-points">-{gap.gap_points} pts</span>
                                </div>
                                <p className="score-breakdown__gap-reason">{gap.reason}</p>
                            </div>
                        ))}
                    </div>
                    {gapAnalysis.improvement_actions && gapAnalysis.improvement_actions.length > 0 && (
                        <>
                            <h5>🎯 Prioritized Actions to Close Gaps</h5>
                            <div className="score-breakdown__items">
                                {gapAnalysis.improvement_actions.map((action, i) => (
                                    <div key={i} className="score-breakdown__item score-breakdown__item--rec">{action}</div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}

            {breakdown.compare_mode && (
                <div className="score-breakdown__meta">
                    <h4>⚖️ Provider Compare</h4>
                    <div className="score-breakdown__tag-list">
                        <span className="score-breakdown__tag">
                            Best: {(breakdown.best_provider || 'unknown').toString().toUpperCase()}
                        </span>
                        <span className="score-breakdown__tag">
                            Providers: {Object.keys(breakdown.results ?? {}).join(', ') || 'N/A'}
                        </span>
                    </div>
                </div>
            )}

            {/* ── Scored at ─────────────────────────────────────── */}
            {breakdown.scored_at && (
                <div className="score-breakdown__scored-at">
                    Scored at {new Date(breakdown.scored_at).toLocaleString()}
                </div>
            )}
        </div>
    );
}
