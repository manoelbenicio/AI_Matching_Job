'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useUIStore } from '@/stores/app-store';
import type { CvEnhanceRequest, CvEnhanceResponse, CvVersion, AuditEvent } from '@/lib/types';

// === Enhance CV mutation ===
export function useEnhanceCv() {
    const queryClient = useQueryClient();
    const { addToast } = useUIStore();

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
        },

        onError: () => {
            addToast({ type: 'error', message: 'Failed to enhance CV. Check your API key and try again.' });
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
