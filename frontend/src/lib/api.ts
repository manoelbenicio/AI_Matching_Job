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
};

export { ApiError };
export default api;
