'use client';

import { useEffect, useCallback } from 'react';
import { useAppStore } from '@/stores/app-store';
import { useUIStore } from '@/stores/app-store';
import { useJobs } from '@/hooks/use-jobs';

/**
 * Global keyboard navigation for the job list.
 *  J / ↓  — move focus to next job
 *  K / ↑  — move focus to previous job
 *  Enter  — open detail panel for focused job
 *  Escape — close detail panel / command palette
 */
export function useKeyboardNav() {
    const { data: response } = useJobs();
    const selectedJobId = useAppStore((s) => s.selectedJobId);
    const setSelectedJobId = useAppStore((s) => s.setSelectedJobId);
    const commandPaletteOpen = useUIStore((s) => s.commandPaletteOpen);

    const jobs = response?.data ?? [];

    const handleKeyDown = useCallback(
        (e: KeyboardEvent) => {
            // Don't capture when focus is in an input, select, or textarea
            const tag = (e.target as HTMLElement)?.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

            // Don't capture when command palette is open
            if (commandPaletteOpen) return;

            const currentIndex = jobs.findIndex((j) => j.id === selectedJobId);

            switch (e.key) {
                case 'j':
                case 'ArrowDown': {
                    e.preventDefault();
                    const nextIndex = currentIndex < jobs.length - 1 ? currentIndex + 1 : 0;
                    setSelectedJobId(jobs[nextIndex]?.id ?? null);

                    // Scroll the focused row into view
                    requestAnimationFrame(() => {
                        const row = document.querySelector('.tr--focused');
                        row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                    });
                    break;
                }
                case 'k':
                case 'ArrowUp': {
                    e.preventDefault();
                    const prevIndex = currentIndex > 0 ? currentIndex - 1 : jobs.length - 1;
                    setSelectedJobId(jobs[prevIndex]?.id ?? null);

                    requestAnimationFrame(() => {
                        const row = document.querySelector('.tr--focused');
                        row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                    });
                    break;
                }
                case 'Enter': {
                    if (selectedJobId != null) {
                        e.preventDefault();
                        // Detail panel is already open via selectedJobId — toggle it
                        // If it's already showing, this is a no-op (panel stays open)
                    }
                    break;
                }
                case 'Escape': {
                    if (selectedJobId != null) {
                        e.preventDefault();
                        setSelectedJobId(null);
                    }
                    break;
                }
            }
        },
        [jobs, selectedJobId, setSelectedJobId, commandPaletteOpen]
    );

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);
}
