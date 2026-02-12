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

export function ScoreBreakdownTab({ breakdown }: Props) {
    const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

    if (!breakdown) {
        return (
            <div className="score-breakdown__empty">
                <svg width="40" height="40" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3">
                    <path d="M8 1l2 3h3l-2.5 3L12 11l-4-2-4 2 1.5-4L3 4h3L8 1z" />
                </svg>
                <p>No detailed score breakdown yet. Run the AI scoring pipeline to generate a 7-section analysis.</p>
            </div>
        );
    }

    const toggleSection = (idx: number) =>
        setExpandedIdx(expandedIdx === idx ? null : idx);

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
                    <p>{breakdown.model_used} • {breakdown.sections.length} dimensions</p>
                </div>
                <span
                    className={`score-breakdown__interview-badge score-breakdown__interview-badge--${breakdown.interview_probability}`}
                >
                    {breakdown.interview_probability === 'HIGH' && '🟢'}
                    {breakdown.interview_probability === 'MEDIUM' && '🟡'}
                    {breakdown.interview_probability === 'LOW' && '🔴'}
                    {breakdown.interview_probability} Chance
                </span>
            </div>

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
                        <span className="score-section__weight">{Math.round(sec.weight * 100)}%</span>
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
                            {sec.strong_points.length > 0 && (
                                <>
                                    <h5>Strengths</h5>
                                    <div className="score-section__items">
                                        {sec.strong_points.map((p, i) => (
                                            <div key={i} className="score-section__item score-section__item--strong">{p}</div>
                                        ))}
                                    </div>
                                </>
                            )}
                            {sec.weak_points.length > 0 && (
                                <>
                                    <h5>Weaknesses</h5>
                                    <div className="score-section__items">
                                        {sec.weak_points.map((p, i) => (
                                            <div key={i} className="score-section__item score-section__item--weak">{p}</div>
                                        ))}
                                    </div>
                                </>
                            )}
                            {sec.recommendations.length > 0 && (
                                <>
                                    <h5>Recommendations</h5>
                                    <div className="score-section__items">
                                        {sec.recommendations.map((p, i) => (
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
            {breakdown.key_risks.length > 0 && (
                <div className="score-breakdown__meta">
                    <h4>⚠️ Key Risks</h4>
                    <div className="score-breakdown__tag-list">
                        {breakdown.key_risks.map((r, i) => (
                            <span key={i} className="score-breakdown__tag score-breakdown__tag--risk">{r}</span>
                        ))}
                    </div>
                </div>
            )}

            {/* ── CV Enhancement priorities ─────────────────────── */}
            {breakdown.cv_enhancement_priorities.length > 0 && (
                <div className="score-breakdown__meta">
                    <h4>🎯 CV Enhancement Priorities</h4>
                    <div className="score-breakdown__tag-list">
                        {breakdown.cv_enhancement_priorities.map((p, i) => (
                            <span key={i} className="score-breakdown__tag score-breakdown__tag--priority">{p}</span>
                        ))}
                    </div>
                </div>
            )}

            {/* ── Scored at ─────────────────────────────────────── */}
            <div className="score-breakdown__scored-at">
                Scored at {new Date(breakdown.scored_at).toLocaleString()}
            </div>
        </div>
    );
}
