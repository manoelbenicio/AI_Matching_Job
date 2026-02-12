'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';

// ── Icons ────────────────────────────────────────────────────────────────
const CloseIcon = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
);

const TrashIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M2 4h12M5.3 4V2.7a1.3 1.3 0 0 1 1.4-1.4h2.6a1.3 1.3 0 0 1 1.4 1.4V4M6.7 7.3v4M9.3 7.3v4" />
        <path d="M3.3 4h9.4l-.8 9.6a1.3 1.3 0 0 1-1.4 1.1H5.5a1.3 1.3 0 0 1-1.4-1.1L3.3 4z" />
    </svg>
);

const UploadIcon = () => (
    <svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M8 10V2M8 2l-3 3M8 2l3 3" />
        <path d="M2 10v3a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-3" />
    </svg>
);

const StarIcon = ({ filled }: { filled: boolean }) => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.5">
        <path d="M8 1l2 3h3l-2.5 3L12 11l-4-2-4 2 1.5-4L3 4h3L8 1z" />
    </svg>
);

// ── Types ────────────────────────────────────────────────────────────────
interface Candidate {
    id: number;
    name: string;
    email: string;
    is_active: boolean;
    created_at: string;
    resume_preview: string;
}

// ── Component ────────────────────────────────────────────────────────────
export function CvManagerModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadStep, setUploadStep] = useState<'idle' | 'preview' | 'naming'>('idle');
    const [parsedText, setParsedText] = useState('');
    const [cvName, setCvName] = useState('');
    const [cvEmail, setCvEmail] = useState('');
    const [dragOver, setDragOver] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (open) loadCandidates();
    }, [open]);

    const loadCandidates = async () => {
        setLoading(true);
        try {
            const data = await api.getCandidates();
            setCandidates(data);
        } catch {
            setError('Failed to load CVs');
        }
        setLoading(false);
    };

    const handleFileSelect = async (file: File) => {
        const allowed = ['.txt', '.pdf', '.docx', '.doc'];
        const ext = '.' + file.name.split('.').pop()?.toLowerCase();
        if (!allowed.includes(ext)) {
            setError('Unsupported file type. Use .txt, .pdf, or .docx');
            return;
        }

        setUploading(true);
        setError('');
        try {
            const resp = await api.uploadCv(file);
            setParsedText(resp.text || '');
            setCvName(file.name.replace(/\.[^.]+$/, ''));
            setUploadStep('preview');
        } catch (e: any) {
            setError('Failed to parse file');
        }
        setUploading(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFileSelect(file);
    };

    const handleSaveCV = async () => {
        if (!cvName.trim() || !parsedText) return;
        setUploading(true);
        try {
            await api.createCandidate({
                name: cvName.trim(),
                email: cvEmail.trim() || undefined,
                resume_text: parsedText,
            });
            setUploadStep('idle');
            setParsedText('');
            setCvName('');
            setCvEmail('');
            await loadCandidates();
        } catch {
            setError('Failed to save CV');
        }
        setUploading(false);
    };

    const handleSetActive = async (id: number) => {
        try {
            await api.setActiveCandidate(id);
            await loadCandidates();
        } catch {
            setError('Failed to set active');
        }
    };

    const handleDelete = async (id: number) => {
        try {
            await api.deleteCandidate(id);
            await loadCandidates();
        } catch {
            setError('Failed to delete');
        }
    };

    if (!open) return null;

    return (
        <div className="scoring-overlay" onClick={onClose}>
            <div className="settings-panel cv-panel" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="scoring-panel__header">
                    <div className="scoring-panel__title">
                        <h2>📄 CV Manager</h2>
                        <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>Upload & manage your resumes</span>
                    </div>
                    <button className="scoring-panel__close" onClick={onClose}><CloseIcon /></button>
                </div>

                {/* Body */}
                <div className="settings-body">
                    {error && <div className="settings-save-msg settings-save-msg--error">{error}</div>}

                    {/* Upload Zone */}
                    {uploadStep === 'idle' && (
                        <div
                            className={`cv-upload-zone ${dragOver ? 'cv-upload-zone--active' : ''}`}
                            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".txt,.pdf,.docx,.doc"
                                style={{ display: 'none' }}
                                onChange={e => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                            />
                            {uploading ? (
                                <div className="cv-upload-zone__content">
                                    <svg className="settings-spinner" width="24" height="24" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M8 1a7 7 0 1 0 7 7" />
                                    </svg>
                                    <span>Parsing file…</span>
                                </div>
                            ) : (
                                <div className="cv-upload-zone__content">
                                    <UploadIcon />
                                    <span><strong>Drop a CV file here</strong> or click to browse</span>
                                    <span className="cv-upload-zone__hint">.txt, .pdf, .docx supported</span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Preview + Name step */}
                    {uploadStep === 'preview' && (
                        <div className="cv-preview-section">
                            <label className="settings-field__label">Parsed Text Preview</label>
                            <pre className="cv-preview-text">{parsedText.slice(0, 800)}{parsedText.length > 800 ? '…' : ''}</pre>
                            <div className="cv-preview-fields">
                                <div className="settings-field">
                                    <label className="settings-field__label">CV Name *</label>
                                    <input
                                        className="settings-field__input"
                                        value={cvName}
                                        onChange={e => setCvName(e.target.value)}
                                        placeholder="e.g. My Resume 2024"
                                    />
                                </div>
                                <div className="settings-field">
                                    <label className="settings-field__label">Email (optional)</label>
                                    <input
                                        className="settings-field__input"
                                        value={cvEmail}
                                        onChange={e => setCvEmail(e.target.value)}
                                        placeholder="you@example.com"
                                    />
                                </div>
                            </div>
                            <div className="cv-preview-actions">
                                <button className="btn btn--ghost" onClick={() => { setUploadStep('idle'); setParsedText(''); }}>Cancel</button>
                                <button className="btn btn--primary" onClick={handleSaveCV} disabled={uploading || !cvName.trim()}>
                                    {uploading ? 'Saving…' : 'Save CV'}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* CV List */}
                    <div className="cv-list">
                        <label className="settings-field__label" style={{ marginBottom: '0.5rem' }}>
                            Saved CVs {candidates.length > 0 && `(${candidates.length})`}
                        </label>
                        {loading ? (
                            <div style={{ textAlign: 'center', padding: '2rem', opacity: 0.5 }}>Loading…</div>
                        ) : candidates.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '2rem', opacity: 0.5 }}>No CVs uploaded yet</div>
                        ) : (
                            candidates.map(c => (
                                <div key={c.id} className={`cv-card ${c.is_active ? 'cv-card--active' : ''}`}>
                                    <div className="cv-card__info">
                                        <div className="cv-card__name">
                                            {c.is_active && <span className="cv-card__active-badge">Active</span>}
                                            {c.name}
                                        </div>
                                        <div className="cv-card__preview">{c.resume_preview}</div>
                                        <div className="cv-card__meta">
                                            {c.email && <span>{c.email}</span>}
                                            <span>{new Date(c.created_at).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                    <div className="cv-card__actions">
                                        {!c.is_active && (
                                            <button className="btn btn--sm btn--ghost" onClick={() => handleSetActive(c.id)} title="Set as Active CV">
                                                <StarIcon filled={false} /> Use
                                            </button>
                                        )}
                                        <button className="btn btn--sm btn--ghost cv-card__delete" onClick={() => handleDelete(c.id)} title="Delete CV">
                                            <TrashIcon />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
