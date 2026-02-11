'use client';

import { useState, useRef, useCallback } from 'react';
import { useEnhanceCv, useCvVersions } from '@/hooks/use-cv';
import { useUIStore } from '@/stores/app-store';
import { FitScoreChart } from './fit-score-chart';
import { CvDiffView } from './cv-diff-view';
import { CvVersionHistory } from './cv-version-history';
import type { Job, CvVersion, CvEnhanceResponse } from '@/lib/types';
import './cv-tab.css';

interface CvTabProps {
    job: Job;
}

export function CvTab({ job }: CvTabProps) {
    const [enhanceResult, setEnhanceResult] = useState<CvEnhanceResponse | null>(null);
    const [selectedVersion, setSelectedVersion] = useState<CvVersion | null>(null);
    const [uploadedText, setUploadedText] = useState<string | null>(null);
    const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const { addToast } = useUIStore();

    const enhanceMutation = useEnhanceCv();
    const { data: versions } = useCvVersions(job.id);

    // ── Drag-and-drop handlers ──
    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    }, []);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
    }, []);

    const handleFile = (file: File) => {
        setIsUploading(true);
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target?.result;
            if (typeof text === 'string') {
                setUploadedText(text);
                setUploadedFileName(file.name);
                const sizeKb = Math.round(file.size / 1024);
                addToast({ type: 'success', message: `CV uploaded: ${file.name} (${sizeKb} KB)` });
            }
            setIsUploading(false);
        };
        reader.onerror = () => {
            addToast({ type: 'error', message: 'Failed to read file. Try a .txt file.' });
            setIsUploading(false);
        };
        reader.readAsText(file);
    };

    // ── Enhance handler ──
    const handleEnhance = () => {
        enhanceMutation.mutate(
            {
                job_id: job.id,
                resume_text: uploadedText || 'Professional experience in software engineering, data analysis, and project management.',
            },
            {
                onSuccess: (result) => {
                    setEnhanceResult(result);
                },
            }
        );
    };

    const fitLevel = (score: number) => {
        if (score >= 85) return 'excellent';
        if (score >= 70) return 'great';
        if (score >= 55) return 'good';
        if (score >= 35) return 'partial';
        return 'weak';
    };

    // ── If viewing a specific version ──
    if (selectedVersion) {
        return (
            <div className="cv-tab">
                <button
                    className="cv-tab__back-btn"
                    onClick={() => setSelectedVersion(null)}
                >
                    ← Back to CV Analysis
                </button>
                <div className="cv-tab__version-detail">
                    <div className="cv-tab__version-detail-header">
                        <h3 className="cv-tab__result-title">
                            Version {selectedVersion.version_number}
                        </h3>
                        <span
                            className="cv-tab__fit-score"
                            data-level={fitLevel(selectedVersion.fit_score ?? 0)}
                        >
                            {selectedVersion.fit_score ?? 'N/A'}/100
                        </span>
                    </div>

                    {/* Skills */}
                    {(selectedVersion.skills_matched?.length > 0 || selectedVersion.skills_missing?.length > 0) && (
                        <div className="cv-tab__skills">
                            {selectedVersion.skills_matched?.length > 0 && (
                                <div className="cv-tab__skill-group">
                                    <span className="cv-tab__skill-label">Matched Skills</span>
                                    <div className="cv-tab__pills">
                                        {selectedVersion.skills_matched.map((s) => (
                                            <span key={s} className="cv-tab__pill cv-tab__pill--matched">{s}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {selectedVersion.skills_missing?.length > 0 && (
                                <div className="cv-tab__skill-group">
                                    <span className="cv-tab__skill-label">Missing Skills</span>
                                    <div className="cv-tab__pills">
                                        {selectedVersion.skills_missing.map((s) => (
                                            <span key={s} className="cv-tab__pill cv-tab__pill--missing">{s}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Content preview */}
                    <div className="cv-tab__content-preview">
                        <p className="cv-tab__content-label">Enhanced Content</p>
                        <pre className="cv-tab__content-text">
                            {selectedVersion.enhanced_content}
                        </pre>
                    </div>
                </div>
            </div>
        );
    }

    // ── Main view ──
    return (
        <div className="cv-tab">
            {/* Upload zone */}
            <div
                className={`cv-tab__upload-zone ${isDragging ? 'cv-tab__upload-zone--active' : ''} ${uploadedFileName ? 'cv-tab__upload-zone--has-file' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                aria-label="Upload CV file"
                onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        fileInputRef.current?.click();
                    }
                }}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt,.pdf,.docx,.doc"
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                    aria-hidden="true"
                />

                {isUploading ? (
                    <div className="cv-tab__upload-loading">
                        <div className="cv-tab__spinner" />
                        <span>Uploading...</span>
                    </div>
                ) : uploadedFileName ? (
                    <div className="cv-tab__upload-success">
                        <span className="cv-tab__upload-icon">📄</span>
                        <span className="cv-tab__upload-filename">{uploadedFileName}</span>
                        <span className="cv-tab__upload-change">Click or drop to change</span>
                    </div>
                ) : (
                    <>
                        <span className="cv-tab__upload-icon">📁</span>
                        <p className="cv-tab__upload-text">
                            <strong>Drop your CV here</strong> or click to browse
                        </p>
                        <p className="cv-tab__upload-hint">.txt, .pdf, .docx supported</p>
                    </>
                )}
            </div>

            {/* Enhance button */}
            <div className="cv-tab__actions">
                <button
                    className="cv-tab__enhance-btn"
                    onClick={handleEnhance}
                    disabled={enhanceMutation.isPending}
                    aria-label="Enhance CV with AI"
                >
                    {enhanceMutation.isPending ? (
                        <>
                            <div className="cv-tab__spinner" />
                            Enhancing with AI…
                        </>
                    ) : (
                        <>
                            <span className="cv-tab__icon">✨</span>
                            {uploadedText ? 'Enhance Uploaded CV' : 'Enhance CV'}
                        </>
                    )}
                </button>
            </div>

            {/* Enhancement result */}
            {enhanceResult && (
                <div className="cv-tab__result">
                    <div className="cv-tab__result-header">
                        <h3 className="cv-tab__result-title">Enhancement Result</h3>
                        <span
                            className="cv-tab__fit-score"
                            data-level={fitLevel(enhanceResult.fit_score)}
                        >
                            {enhanceResult.fit_score}/100
                        </span>
                    </div>

                    {/* Fit Score Chart */}
                    <FitScoreChart
                        fitScore={enhanceResult.fit_score}
                        matchedCount={enhanceResult.skills_matched?.length || 0}
                        missingCount={enhanceResult.skills_missing?.length || 0}
                    />

                    {/* Skills */}
                    <div className="cv-tab__skills">
                        {enhanceResult.skills_matched?.length > 0 && (
                            <div className="cv-tab__skill-group">
                                <span className="cv-tab__skill-label">Matched Skills</span>
                                <div className="cv-tab__pills">
                                    {enhanceResult.skills_matched.map((s) => (
                                        <span key={s} className="cv-tab__pill cv-tab__pill--matched">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {enhanceResult.skills_missing?.length > 0 && (
                            <div className="cv-tab__skill-group">
                                <span className="cv-tab__skill-label">Missing Skills</span>
                                <div className="cv-tab__pills">
                                    {enhanceResult.skills_missing.map((s) => (
                                        <span key={s} className="cv-tab__pill cv-tab__pill--missing">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Diff */}
                    {enhanceResult.diff && enhanceResult.diff.length > 0 && (
                        <CvDiffView diff={enhanceResult.diff} />
                    )}
                </div>
            )}

            {/* Version History */}
            {versions && versions.length > 0 && (
                <div>
                    <h3 className="cv-tab__section-title">Version History</h3>
                    <CvVersionHistory
                        versions={versions}
                        selectedId={null}
                        onSelect={setSelectedVersion}
                    />
                </div>
            )}

            {/* Empty state */}
            {!enhanceResult && (!versions || versions.length === 0) && (
                <div className="cv-tab__empty">
                    <p>Upload your CV and click Enhance to get AI-powered suggestions.</p>
                    <p className="cv-tab__empty-hint">
                        The AI will analyze your resume against this job&apos;s requirements.
                    </p>
                </div>
            )}
        </div>
    );
}
