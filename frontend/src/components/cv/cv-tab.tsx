'use client';

import { useState, useRef, useCallback } from 'react';
import { useEnhanceCv, useCvVersions } from '@/hooks/use-cv';
import { useJobStats } from '@/hooks/use-jobs';
import { useUIStore } from '@/stores/app-store';
import { FitScoreChart } from './fit-score-chart';
import { CvDiffView } from './cv-diff-view';
import { CvVersionHistory } from './cv-version-history';
import api, { ApiError } from '@/lib/api';
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
    const [isExporting, setIsExporting] = useState(false);
    const [isArchiving, setIsArchiving] = useState(false);
    const [isExportingHtmlAts, setIsExportingHtmlAts] = useState(false);
    const [isExportingHtmlPremium, setIsExportingHtmlPremium] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const { addToast } = useUIStore();

    const enhanceMutation = useEnhanceCv();
    const { data: versions } = useCvVersions(job.id);
    const { data: stats } = useJobStats();
    const qualificationThreshold = stats?.qualification_threshold ?? 80;

    const canExport = (job.score ?? 0) >= qualificationThreshold && versions && versions.length > 0;
    const safeCompany = (job.company_name || 'Company').replace(/\s+/g, '_');
    const safeTitle = (job.job_title || 'Role').replace(/\s+/g, '_');

    const apiErrorMessage = (err: unknown, fallback: string): string => {
        if (err instanceof ApiError) {
            if (typeof err.body === 'string' && err.body.trim()) return err.body;
            if (err.body && typeof err.body === 'object' && 'detail' in err.body) {
                const detail = (err.body as { detail?: unknown }).detail;
                if (typeof detail === 'string' && detail.trim()) return detail;
            }
            return `${fallback} (HTTP ${err.status})`;
        }
        return err instanceof Error && err.message ? err.message : fallback;
    };

    // ── Premium Export ──
    const handlePremiumExport = async () => {
        setIsExporting(true);
        try {
            const blob = await api.downloadPremiumCv(job.id);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `CV_${job.company_name?.replace(/\s+/g, '_')}_${job.job_title?.replace(/\s+/g, '_')}_ATS.docx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            addToast({ type: 'success', message: 'Premium CV exported! Check your downloads.' });
        } catch (err: unknown) {
            const msg = apiErrorMessage(err, 'Premium DOCX export failed');
            addToast({ type: 'error', message: msg });
        } finally {
            setIsExporting(false);
        }
    };

    // ── Archive to Google Drive ──
    const handleArchiveToDrive = async () => {
        setIsArchiving(true);
        try {
            const result = await api.archiveToDrive(job.id);
            addToast({
                type: 'success',
                message: `Archived to Google Drive: ${result.filename}`,
            });
            if (result.drive_url) {
                window.open(result.drive_url, '_blank');
            }
        } catch (err: unknown) {
            const msg = apiErrorMessage(err, 'Google Drive archive failed');
            addToast({ type: 'error', message: msg });
        } finally {
            setIsArchiving(false);
        }
    };

    const _downloadHtml = (html: string, filename: string) => {
        if (!html || !html.trim()) {
            throw new Error('Empty HTML payload received from server.');
        }
        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handlePremiumHtmlAts = async () => {
        setIsExportingHtmlAts(true);
        try {
            const res = await api.premiumHtml(job.id, 'ats');
            _downloadHtml(res.html, `CV_${safeCompany}_${safeTitle}_ATS.html`);
            addToast({ type: 'success', message: 'ATS HTML exported.' });
        } catch (err: unknown) {
            const msg = apiErrorMessage(err, 'ATS HTML export failed');
            addToast({ type: 'error', message: msg });
        } finally {
            setIsExportingHtmlAts(false);
        }
    };

    const handlePremiumHtmlOpen = async () => {
        setIsExportingHtmlPremium(true);
        try {
            const res = await api.premiumHtml(job.id, 'premium');
            const win = window.open('', '_blank');
            if (win) {
                win.document.open();
                win.document.write(res.html);
                win.document.close();
                addToast({ type: 'success', message: 'Premium HTML opened in new tab.' });
            } else {
                _downloadHtml(res.html, `CV_${safeCompany}_${safeTitle}_Premium.html`);
                addToast({ type: 'success', message: 'Popup blocked; Premium HTML downloaded.' });
            }
        } catch (err: unknown) {
            const msg = apiErrorMessage(err, 'Premium HTML export failed');
            addToast({ type: 'error', message: msg });
        } finally {
            setIsExportingHtmlPremium(false);
        }
    };

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

    const handleFile = async (file: File) => {
        setIsUploading(true);
        try {
            // Always parse via backend to correctly handle .pdf/.docx/.doc/.txt.
            const parsed = await api.uploadCv(file);
            setUploadedText(parsed.text);
            setUploadedFileName(parsed.filename || file.name);
            const sizeKb = Math.round((parsed.size_bytes || file.size) / 1024);
            addToast({ type: 'success', message: `CV uploaded: ${file.name} (${sizeKb} KB)` });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to parse uploaded file.';
            addToast({ type: 'error', message: msg });
        } finally {
            setIsUploading(false);
        }
    };

    // ── Enhance handler ──
    const handleEnhance = () => {
        enhanceMutation.mutate(
            {
                job_id: job.id,
                // If no file is uploaded, let backend resolve the active/default resume source.
                resume_text: uploadedText || undefined,
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
                        {selectedVersion.enhanced_content ? (
                            <div
                                className="cv-tab__content-html"
                                dangerouslySetInnerHTML={{ __html: selectedVersion.enhanced_content }}
                            />
                        ) : (
                            <p className="cv-tab__content-text">No enhanced content available.</p>
                        )}
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
                    className="cv-tab__enhance-btn cv-tab__enhance-btn--primary"
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

                {canExport && (
                    <button
                        className="cv-tab__enhance-btn cv-tab__enhance-btn--secondary cv-tab__enhance-btn--export"
                        onClick={handlePremiumExport}
                        disabled={isExporting}
                        aria-label="Download ATS-optimized DOCX"
                    >
                        {isExporting ? (
                            <>
                                <div className="cv-tab__spinner" />
                                Generating DOCX…
                            </>
                        ) : (
                            <>
                                <span className="cv-tab__icon">📥</span>
                                Download DOCX
                            </>
                        )}
                    </button>
                )}

                {canExport && (
                    <button
                        className="cv-tab__enhance-btn cv-tab__enhance-btn--secondary cv-tab__enhance-btn--drive"
                        onClick={handleArchiveToDrive}
                        disabled={isArchiving}
                        aria-label="Archive enhanced CV to Google Drive"
                    >
                        {isArchiving ? (
                            <>
                                <div className="cv-tab__spinner" />
                                Archiving…
                            </>
                        ) : (
                            <>
                                <span className="cv-tab__icon">☁️</span>
                                Archive Drive
                            </>
                        )}
                    </button>
                )}

                {canExport && (
                    <button
                        className="cv-tab__enhance-btn cv-tab__enhance-btn--secondary cv-tab__enhance-btn--export"
                        onClick={handlePremiumHtmlAts}
                        disabled={isExportingHtmlAts}
                        aria-label="Download ATS HTML resume"
                    >
                        {isExportingHtmlAts ? (
                            <>
                                <div className="cv-tab__spinner" />
                                Generating ATS HTML…
                            </>
                        ) : (
                            <>
                                <span className="cv-tab__icon">🧾</span>
                                Download ATS HTML
                            </>
                        )}
                    </button>
                )}

                {canExport && (
                    <button
                        className="cv-tab__enhance-btn cv-tab__enhance-btn--secondary cv-tab__enhance-btn--drive"
                        onClick={handlePremiumHtmlOpen}
                        disabled={isExportingHtmlPremium}
                        aria-label="Open premium HTML resume"
                    >
                        {isExportingHtmlPremium ? (
                            <>
                                <div className="cv-tab__spinner" />
                                Generating Premium HTML…
                            </>
                        ) : (
                            <>
                                <span className="cv-tab__icon">🌐</span>
                                Open Premium HTML
                            </>
                        )}
                    </button>
                )}
            </div>
            {!canExport && (job.score ?? 0) > 0 && (
                <p className="cv-tab__export-hint">
                    Premium export is available for scores ≥ {qualificationThreshold}% and at least one enhanced CV version.
                </p>
            )}

            {/* Enhancement result */}
            {enhanceResult && (
                <div className="cv-tab__result">
                    {(() => {
                        const fallbackFit = (job.detailed_score?.overall_score ?? job.score ?? 0);
                        const rawFit = Number(enhanceResult.fit_score ?? 0);
                        const displayFit = rawFit > 0 ? rawFit : fallbackFit;
                        const displayMatched = (enhanceResult.skills_matched?.length ?? 0) > 0
                            ? (enhanceResult.skills_matched ?? [])
                            : (job.detailed_score?.skills_matched ?? []);
                        const displayMissing = (enhanceResult.skills_missing?.length ?? 0) > 0
                            ? (enhanceResult.skills_missing ?? [])
                            : (job.detailed_score?.skills_missing ?? []);
                        return (
                            <>
                    <div className="cv-tab__result-header">
                        <h3 className="cv-tab__result-title">Enhancement Result</h3>
                        <span
                            className="cv-tab__fit-score"
                            data-level={fitLevel(displayFit)}
                        >
                            {displayFit}/100
                        </span>
                    </div>

                    {/* Fit Score Chart */}
                    <FitScoreChart
                        fitScore={displayFit}
                        matchedCount={displayMatched.length || 0}
                        missingCount={displayMissing.length || 0}
                    />

                    {/* Skills */}
                    <div className="cv-tab__skills">
                        {displayMatched.length > 0 && (
                            <div className="cv-tab__skill-group">
                                <span className="cv-tab__skill-label">Matched Skills</span>
                                <div className="cv-tab__pills">
                                    {displayMatched.map((s) => (
                                        <span key={s} className="cv-tab__pill cv-tab__pill--matched">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {displayMissing.length > 0 && (
                            <div className="cv-tab__skill-group">
                                <span className="cv-tab__skill-label">Missing Skills</span>
                                <div className="cv-tab__pills">
                                    {displayMissing.map((s) => (
                                        <span key={s} className="cv-tab__pill cv-tab__pill--missing">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Enhanced CV HTML Preview */}
                    {enhanceResult.enhanced_cv && (
                        <details className="cv-tab__content-preview" open>
                            <summary className="cv-tab__content-label">
                                📄 Enhanced Resume Preview
                            </summary>
                            <div
                                className="cv-tab__content-html"
                                dangerouslySetInnerHTML={{ __html: enhanceResult.enhanced_cv }}
                            />
                        </details>
                    )}

                    {/* Diff */}
                    {enhanceResult.diff && enhanceResult.diff.length > 0 && (
                        <CvDiffView diff={enhanceResult.diff} />
                    )}
                            </>
                        );
                    })()}
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
