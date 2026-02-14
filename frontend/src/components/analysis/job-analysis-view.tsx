'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAppStore, useUIStore } from '@/stores/app-store';
import { useJob } from '@/hooks/use-jobs';
import { ScoreBreakdownTab } from '@/components/detail-panel/score-breakdown-tab';
import { CvTab } from '@/components/cv/cv-tab';
import api from '@/lib/api';
import type { Job } from '@/lib/types';
import './job-analysis-view.css';

// ── API Key Panel ────────────────────────────────────────────────────────

function ApiKeyPanel() {
    const addToast = useUIStore((s) => s.addToast);
    const [openaiKey, setOpenaiKey] = useState('');
    const [geminiKey, setGeminiKey] = useState('');
    const [openaiSet, setOpenaiSet] = useState(false);
    const [geminiSet, setGeminiSet] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        api.getSettings().then((s) => {
            setOpenaiSet(s.openai_key_set);
            setGeminiSet(s.gemini_key_set);
        }).catch(() => { /* ignore */ });
    }, []);

    const handleSave = async () => {
        const data: { openai_api_key?: string; gemini_api_key?: string } = {};
        if (openaiKey.trim()) data.openai_api_key = openaiKey.trim();
        if (geminiKey.trim()) data.gemini_api_key = geminiKey.trim();
        if (!data.openai_api_key && !data.gemini_api_key) return;

        setSaving(true);
        try {
            const res = await api.saveApiKeys(data);
            addToast({ type: 'success', message: res.message });
            if (data.openai_api_key) { setOpenaiSet(true); setOpenaiKey(''); }
            if (data.gemini_api_key) { setGeminiSet(true); setGeminiKey(''); }
        } catch {
            addToast({ type: 'error', message: 'Failed to save API keys' });
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="analysis__api-keys">
            <h3 className="analysis__section-title">🔑 API Keys</h3>
            <div className="analysis__api-key-row">
                <label>OpenAI</label>
                <input
                    type="password"
                    placeholder={openaiSet ? '••••••• (set)' : 'sk-...'}
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                />
                {openaiSet && <span className="analysis__key-badge">✓</span>}
            </div>
            <div className="analysis__api-key-row">
                <label>Gemini</label>
                <input
                    type="password"
                    placeholder={geminiSet ? '••••••• (set)' : 'AIza...'}
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                />
                {geminiSet && <span className="analysis__key-badge">✓</span>}
            </div>
            <button
                className="analysis__save-keys-btn"
                onClick={handleSave}
                disabled={saving || (!openaiKey.trim() && !geminiKey.trim())}
            >
                {saving ? 'Saving…' : 'Save Keys'}
            </button>
        </div>
    );
}

// ── Job Info (Left Column) ──────────────────────────────────────────────

function JobInfoColumn({ job }: { job: Job }) {
    return (
        <div className="analysis__col analysis__col--left">
            <div className="analysis__job-header">
                <h2 className="analysis__job-title">{job.job_title}</h2>
                <p className="analysis__company">{job.company_name}</p>
            </div>

            <div className="analysis__info-grid">
                {job.location && <InfoRow label="Location" value={job.location} />}
                {job.work_type && <InfoRow label="Work Type" value={job.work_type} />}
                {job.employment_type && <InfoRow label="Employment" value={job.employment_type} />}
                {job.seniority_level && <InfoRow label="Seniority" value={job.seniority_level} />}
                {job.salary_info && <InfoRow label="Salary" value={job.salary_info} />}
                {job.sector && <InfoRow label="Sector" value={job.sector} />}
            </div>

            {/* Score hero */}
            {job.score !== null && (
                <div className={`analysis__score-hero ${scoreClass(job.score)}`}>
                    <span className="analysis__score-value">{job.score}</span>
                    <span className="analysis__score-label">Match Score</span>
                </div>
            )}

            {/* Status */}
            <div className="analysis__status-badge" data-status={job.status}>
                {job.status}
            </div>

            {/* LinkedIn link */}
            {job.job_url && (
                <a
                    className="analysis__linkedin-link"
                    href={job.job_url}
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    🔗 View Job Posting
                </a>
            )}

            {/* Description */}
            {job.job_description && (
                <div className="analysis__description">
                    <h3 className="analysis__section-title">Job Description</h3>
                    <div className="analysis__description-text">
                        {job.job_description}
                    </div>
                </div>
            )}
        </div>
    );
}

function InfoRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="analysis__info-row">
            <span className="analysis__info-label">{label}</span>
            <span className="analysis__info-value">{value}</span>
        </div>
    );
}

function scoreClass(score: number): string {
    if (score >= 90) return 'analysis__score-hero--excellent';
    if (score >= 70) return 'analysis__score-hero--good';
    if (score >= 50) return 'analysis__score-hero--partial';
    return 'analysis__score-hero--weak';
}

// ── Main Component ──────────────────────────────────────────────────────

export function JobAnalysisView() {
    const { analysisJobId, closeAnalysis, markDataRefresh } = useAppStore();
    const addToast = useUIStore((s) => s.addToast);
    const { data: job, isLoading, error, refetch } = useJob(analysisJobId!);
    const [scoring, setScoring] = useState(false);
    const [scoreProgress, setScoreProgress] = useState(0);
    const [aiModel, setAiModel] = useState<'openai' | 'gemini' | 'compare'>('openai');

    // Keyboard shortcut: Escape closes analysis
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') closeAnalysis();
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [closeAnalysis]);

    useEffect(() => {
        if (!scoring) return;
        setScoreProgress((prev) => (prev > 0 ? prev : 8));
        const timer = window.setInterval(() => {
            setScoreProgress((prev) => {
                if (prev >= 92) return prev;
                return prev < 50 ? prev + 7 : prev + 3;
            });
        }, 450);
        return () => window.clearInterval(timer);
    }, [scoring]);

    const handleScore = useCallback(async () => {
        if (!analysisJobId || scoring) return;
        setScoring(true);
        setScoreProgress(8);
        try {
            await api.scoreSingleJob(analysisJobId, aiModel);
            setScoreProgress(100);
            const label = aiModel === 'compare' ? 'Compared (OpenAI + Gemini)' : aiModel === 'gemini' ? 'Gemini' : 'OpenAI';
            addToast({ type: 'success', message: `Job scored with ${label}!` });
            markDataRefresh();
            refetch();
        } catch (err: unknown) {
            setScoreProgress(100);
            const msg = err instanceof Error ? err.message : 'Scoring failed';
            addToast({ type: 'error', message: msg });
        } finally {
            setScoring(false);
            window.setTimeout(() => setScoreProgress(0), 400);
        }
    }, [analysisJobId, scoring, aiModel, addToast, refetch, markDataRefresh]);

    if (!analysisJobId) return null;

    if (isLoading) {
        return (
            <div className="analysis">
                <div className="analysis__loading">
                    <div className="analysis__spinner" />
                    <p>Loading job analysis…</p>
                </div>
            </div>
        );
    }

    if (error || !job) {
        return (
            <div className="analysis">
                <div className="analysis__error">
                    <p>Failed to load job details.</p>
                    <button onClick={closeAnalysis}>← Back to Table</button>
                </div>
            </div>
        );
    }

    return (
        <div className="analysis">
            {/* Top bar */}
            <div className="analysis__topbar">
                <button className="analysis__back-btn" onClick={closeAnalysis}>
                    ← Back
                </button>
                <h1 className="analysis__topbar-title">
                    Job Analysis — {job.job_title}
                </h1>
                <div className="analysis__topbar-actions">
                    <select
                        className="analysis__model-select"
                        value={aiModel}
                        onChange={(e) => setAiModel(e.target.value as 'openai' | 'gemini' | 'compare')}
                        disabled={scoring}
                    >
                        <option value="openai">🟢 OpenAI</option>
                        <option value="gemini">🔵 Gemini</option>
                        <option value="compare">⚡ Compare Both</option>
                    </select>
                    <button
                        className="analysis__score-btn"
                        onClick={handleScore}
                        disabled={scoring}
                    >
                        {scoring ? '⏳ Scoring…' : '🎯 Score This Job'}
                    </button>
                </div>
            </div>
            <div
                className={`analysis__score-progress ${scoreProgress > 0 ? 'analysis__score-progress--visible' : ''}`}
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(scoreProgress)}
            >
                <div
                    className="analysis__score-progress-bar"
                    style={{ width: `${Math.max(0, Math.min(100, scoreProgress))}%` }}
                />
            </div>

            {/* Adaptive layout: 2-col when unscored, 3-col when scored */}
            <div className={`analysis__grid ${!job.detailed_score ? 'analysis__grid--two-col' : ''}`}>
                {/* Left: Job details */}
                <JobInfoColumn job={job} />

                {/* Center: Score breakdown (only when scored) */}
                {job.detailed_score && (
                    <div className="analysis__col analysis__col--center">
                        <h3 className="analysis__section-title">📊 Score Breakdown</h3>
                        <ScoreBreakdownTab breakdown={job.detailed_score} />
                    </div>
                )}

                {/* Right: API keys + CV + actions */}
                <div className="analysis__col analysis__col--right">
                    <ApiKeyPanel />

                    <div className="analysis__cv-section">
                        <h3 className="analysis__section-title">🤖 CV Analysis</h3>
                        <CvTab job={job} />
                    </div>
                </div>
            </div>
        </div>
    );
}
