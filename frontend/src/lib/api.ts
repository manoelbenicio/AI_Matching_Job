// === API Client — fetch wrapper for backend communication ===

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

class ApiError extends Error {
    constructor(
        public status: number,
        public statusText: string,
        public body: unknown
    ) {
        super(`API Error ${status}: ${statusText}`);
        this.name = 'ApiError';
    }
}

async function request<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;

    const res = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!res.ok) {
        let body: unknown;
        try {
            body = await res.json();
        } catch {
            body = await res.text();
        }
        throw new ApiError(res.status, res.statusText, body);
    }

    // handle 204 No Content
    if (res.status === 204) {
        return undefined as T;
    }

    return res.json();
}

async function requestFormData<T>(
    endpoint: string,
    formData: FormData
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, {
        method: 'POST',
        body: formData,
        // Do NOT set Content-Type — browser sets it with boundary automatically
    });

    if (!res.ok) {
        let body: unknown;
        try { body = await res.json(); } catch { body = await res.text(); }
        throw new ApiError(res.status, res.statusText, body);
    }
    return res.json();
}

// === API methods ===
export const api = {
    // Jobs
    getJobs: (params?: URLSearchParams) =>
        request<import('./types').JobsResponse>(`/jobs${params ? `?${params}` : ''}`),

    getJob: (id: number) =>
        request<import('./types').Job>(`/jobs/${id}`),

    updateJob: (id: number, data: import('./types').JobUpdate) =>
        request<import('./types').Job>(`/jobs/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    bulkUpdateJobs: (data: import('./types').JobBulkUpdate) =>
        request<{ updated: number }>(`/jobs/bulk`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    getJobStats: () =>
        request<import('./types').JobStats>(`/jobs/stats`),

    // Export jobs to Excel (triggers browser download)
    exportJobsToExcel: (opts?: { status?: string; min_score?: number; ids?: number[] }) => {
        const params = new URLSearchParams();
        if (opts?.status) params.set('status', opts.status);
        if (opts?.min_score) params.set('min_score', String(opts.min_score));
        if (opts?.ids?.length) params.set('ids', opts.ids.join(','));
        const url = `${API_BASE}/jobs/export${params.toString() ? `?${params}` : ''}`;
        // Direct download via anchor click
        const a = document.createElement('a');
        a.href = url;
        a.download = '';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    },

    // CV
    enhanceCv: (data: import('./types').CvEnhanceRequest) =>
        request<import('./types').CvEnhanceResponse>(`/cv/enhance`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    getCvVersions: (jobId: number) =>
        request<import('./types').CvVersion[]>(`/cv/versions/${jobId}`),

    uploadCv: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return requestFormData<import('./types').CvParseResponse>(`/cv/parse`, formData);
    },

    // Audit
    getAuditTrail: (jobId: number) =>
        request<import('./types').AuditEvent[]>(`/audit/${jobId}`),

    // Settings
    getSettings: () =>
        request<{ openai_key_set: boolean; gemini_key_set: boolean; openai_key_preview: string; gemini_key_preview: string }>(`/settings`),

    saveApiKeys: (data: { openai_api_key?: string; gemini_api_key?: string }) =>
        request<{ saved: string[]; message: string }>(`/settings/api-keys`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    testOpenai: () =>
        request<{ ok: boolean; message: string }>(`/settings/test-openai`, { method: 'POST' }),

    testGemini: () =>
        request<{ ok: boolean; message: string }>(`/settings/test-gemini`, { method: 'POST' }),

    // Candidates (CV Management)
    getCandidates: () =>
        request<{ id: number; name: string; email: string; is_active: boolean; created_at: string; resume_preview: string }[]>(`/candidates`),

    createCandidate: (data: { name: string; email?: string; resume_text: string }) =>
        request<{ id: number; name: string }>(`/candidates`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    setActiveCandidate: (id: number) =>
        request<{ message: string }>(`/candidates/${id}/active`, { method: 'PUT' }),

    deleteCandidate: (id: number) =>
        request<{ message: string }>(`/candidates/${id}`, { method: 'DELETE' }),

    getActiveCandidate: () =>
        request<{ id: number; name: string; resume_text: string } | null>(`/candidates/active`),

    // Job Fetch (On-demand) — scrapes any job URL
    fetchJobFromUrl: (url: string) =>
        request<{ success: boolean; already_existed: boolean; job: Record<string, unknown> }>(`/jobs/fetch-url`, {
            method: 'POST',
            body: JSON.stringify({ url }),
        }),

    // Single-job scoring (detailed section-by-section analysis)
    scoreSingleJob: (jobDbId: number) =>
        request<{ success: boolean; job_db_id: number; result: Record<string, unknown> }>(`/scoring/single`, {
            method: 'POST',
            body: JSON.stringify({ job_db_id: jobDbId }),
        }),

    // Premium CV Export (ATS-optimized DOCX download)
    downloadPremiumCv: async (jobId: number, versionId?: number): Promise<Blob> => {
        const res = await fetch(`${API_BASE}/cv/premium-export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: jobId, version_id: versionId }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Export failed' }));
            throw new ApiError(res.status, res.statusText, err.detail || 'Export failed');
        }
        return res.blob();
    },

    // Google Drive archive
    archiveToDrive: (jobId: number, versionId?: number) =>
        request<{ success: boolean; drive_url: string; filename: string }>(`/cv/archive-to-drive`, {
            method: 'POST',
            body: JSON.stringify({ job_id: jobId, version_id: versionId }),
        }),

    // Notifications
    getNotificationSettings: () =>
        request<{ telegram_enabled: boolean; email_enabled: boolean; score_threshold: number }>(`/notifications/settings`),

    saveNotificationSettings: (data: { telegram_enabled?: boolean; email_enabled?: boolean; score_threshold?: number }) =>
        request<{ message: string }>(`/notifications/settings`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    testTelegram: () =>
        request<{ ok: boolean; message: string }>(`/notifications/test-telegram`, { method: 'POST' }),

    testEmail: () =>
        request<{ ok: boolean; message: string }>(`/notifications/test-email`, { method: 'POST' }),
};

export { ApiError };
export default api;

