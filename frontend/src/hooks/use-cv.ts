'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useUIStore } from '@/stores/app-store';
import type { CvVersion, CvEnhanceRequest, CvEnhanceResponse, CvParseResponse, AuditEvent } from '@/lib/types';

// === Fetch CV versions for a job ===
export function useCvVersions(jobId: number | null) {
    return useQuery<CvVersion[]>({
        queryKey: ['cvVersions', jobId],
        queryFn: () => api.getCvVersions(jobId!),
        enabled: jobId !== null,
    });
}

// === Upload CV file ===
export function useUploadCv() {
    const { addToast } = useUIStore();

    return useMutation<CvParseResponse, Error, File>({
        mutationFn: (file) => api.uploadCv(file),

        onSuccess: (result) => {
            const sizeKb = Math.round(result.size_bytes / 1024);
            addToast({ type: 'success', message: `CV uploaded: ${result.filename} (${sizeKb} KB)` });
        },

        onError: () => {
            addToast({ type: 'error', message: 'Failed to upload CV. Try a .txt file.' });
        },
    });
}

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
            // Also invalidate the job itself (status may have changed to "enhanced")
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            queryClient.invalidateQueries({ queryKey: ['job', variables.job_id] });
            queryClient.invalidateQueries({ queryKey: ['jobStats'] });
        },

        onError: () => {
            addToast({ type: 'error', message: 'Failed to enhance CV. Check your API key and try again.' });
        },
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
