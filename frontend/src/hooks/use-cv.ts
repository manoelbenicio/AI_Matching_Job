'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api';
import { useAppStore, useUIStore } from '@/stores/app-store';
import type { CvEnhanceRequest, CvEnhanceResponse, CvVersion, AuditEvent } from '@/lib/types';

// === Enhance CV mutation ===
export function useEnhanceCv() {
    const queryClient = useQueryClient();
    const { addToast } = useUIStore();
    const markDataRefresh = useAppStore((s) => s.markDataRefresh);

    return useMutation<CvEnhanceResponse, Error, CvEnhanceRequest>({
        mutationFn: (data) => api.enhanceCv(data),

        onSuccess: (result, variables) => {
            addToast({ type: 'success', message: `CV enhanced — Fit Score: ${result.fit_score}/100` });
            // Invalidate CV versions to show the new one
            queryClient.invalidateQueries({ queryKey: ['cvVersions', variables.job_id] });
            // Also invalidate audit trail
            queryClient.invalidateQueries({ queryKey: ['audit', variables.job_id] });
            // Invalidate jobs (status may have changed)
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            queryClient.invalidateQueries({ queryKey: ['job', variables.job_id] });
            queryClient.invalidateQueries({ queryKey: ['jobStats'] });
            markDataRefresh();
        },

        onError: (err) => {
            let message = 'Failed to enhance CV. Check your API key and try again.';
            if (err instanceof ApiError) {
                if (typeof err.body === 'string' && err.body.trim()) {
                    message = err.body;
                } else if (err.body && typeof err.body === 'object' && 'detail' in err.body) {
                    const detail = (err.body as { detail?: unknown }).detail;
                    if (typeof detail === 'string' && detail.trim()) {
                        message = detail;
                    }
                }
            } else if (err?.message) {
                message = err.message;
            }
            addToast({ type: 'error', message });
        },
    });
}

// === Fetch CV versions for a job ===
export function useCvVersions(jobId: number | null) {
    return useQuery<CvVersion[]>({
        queryKey: ['cvVersions', jobId],
        queryFn: () => api.getCvVersions(jobId!),
        enabled: jobId !== null,
    });
}

// === Fetch audit trail for a job ===
export function useAuditTrail(jobId: number | null) {
    return useQuery<AuditEvent[]>({
        queryKey: ['audit', jobId],
        queryFn: () => api.getAuditTrail(jobId!),
        enabled: jobId !== null,
    });
}
