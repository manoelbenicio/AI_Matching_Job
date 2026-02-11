'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAppStore } from '@/stores/app-store';
import { useUIStore } from '@/stores/app-store';
import { buildSearchParams } from '@/lib/utils';
import type { Job, JobUpdate, JobBulkUpdate, JobsResponse, JobStats } from '@/lib/types';

// === Fetch all jobs (paginated, filtered, sorted) ===
export function useJobs() {
    const { filters, sort, page, limit } = useAppStore();

    const params = buildSearchParams(filters, sort, page, limit);

    return useQuery<JobsResponse>({
        queryKey: ['jobs', filters, sort, page, limit],
        queryFn: () => api.getJobs(params),
        placeholderData: (previousData) => previousData,
    });
}

// === Fetch single job ===
export function useJob(id: number | null) {
    return useQuery<Job>({
        queryKey: ['job', id],
        queryFn: () => api.getJob(id!),
        enabled: id !== null,
    });
}

// === Fetch job stats ===
export function useJobStats() {
    return useQuery<JobStats>({
        queryKey: ['jobStats'],
        queryFn: () => api.getJobStats(),
        refetchInterval: 60 * 1000, // Auto-refresh every minute
    });
}

// === Update a single job (with optimistic update) ===
export function useUpdateJob() {
    const queryClient = useQueryClient();
    const { addToast } = useUIStore();

    return useMutation({
        mutationFn: ({ id, data }: { id: number; data: JobUpdate }) =>
            api.updateJob(id, data),

        // Optimistic update
        onMutate: async ({ id, data }) => {
            // Cancel any outgoing refetches
            await queryClient.cancelQueries({ queryKey: ['jobs'] });

            // Snapshot the previous value
            const previousJobs = queryClient.getQueriesData<JobsResponse>({ queryKey: ['jobs'] });

            // Optimistically update the cache
            queryClient.setQueriesData<JobsResponse>(
                { queryKey: ['jobs'] },
                (old) => {
                    if (!old) return old;
                    return {
                        ...old,
                        data: old.data.map((job) =>
                            job.id === id
                                ? { ...job, ...data, version: job.version + 1, updated_at: new Date().toISOString() }
                                : job
                        ),
                    };
                }
            );

            return { previousJobs };
        },

        onSuccess: (updatedJob) => {
            addToast({ type: 'success', message: `Updated "${updatedJob.job_title}"` });
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            queryClient.invalidateQueries({ queryKey: ['jobStats'] });
            queryClient.invalidateQueries({ queryKey: ['job', updatedJob.id] });
        },

        onError: (_err, _vars, context) => {
            // Rollback
            if (context?.previousJobs) {
                context.previousJobs.forEach(([queryKey, data]) => {
                    queryClient.setQueryData(queryKey, data);
                });
            }
            addToast({ type: 'error', message: 'Failed to update job. Please try again.' });
        },
    });
}

// === Bulk update jobs ===
export function useBulkUpdateJobs() {
    const queryClient = useQueryClient();
    const { clearSelection } = useAppStore();
    const { addToast } = useUIStore();

    return useMutation({
        mutationFn: (data: JobBulkUpdate) => api.bulkUpdateJobs(data),

        onSuccess: (result) => {
            clearSelection();
            addToast({ type: 'success', message: `Updated ${result.updated} jobs` });
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            queryClient.invalidateQueries({ queryKey: ['jobStats'] });
        },

        onError: () => {
            addToast({ type: 'error', message: 'Failed to bulk update jobs.' });
        },
    });
}
