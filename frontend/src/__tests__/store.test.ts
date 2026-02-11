import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore, useUIStore } from '@/stores/app-store';

// Reset store state between tests
beforeEach(() => {
    useAppStore.setState({
        viewMode: 'table',
        selectedIds: new Set(),
        filters: {
            search: '',
            status: [],
            work_type: [],
            score_min: null,
            score_max: null,
        },
        sort: { column: 'updated_at', direction: 'desc' },
        page: 1,
        limit: 50,
        selectedJobId: null,
    });

    useUIStore.setState({
        commandPaletteOpen: false,
        toasts: [],
    });
});

describe('useAppStore', () => {
    describe('viewMode', () => {
        it('defaults to table', () => {
            expect(useAppStore.getState().viewMode).toBe('table');
        });

        it('switches to kanban', () => {
            useAppStore.getState().setViewMode('kanban');
            expect(useAppStore.getState().viewMode).toBe('kanban');
        });

        it('switches to split', () => {
            useAppStore.getState().setViewMode('split');
            expect(useAppStore.getState().viewMode).toBe('split');
        });
    });

    describe('selection', () => {
        it('toggles selection on', () => {
            useAppStore.getState().toggleSelection(1);
            expect(useAppStore.getState().selectedIds.has(1)).toBe(true);
        });

        it('toggles selection off', () => {
            useAppStore.getState().toggleSelection(1);
            useAppStore.getState().toggleSelection(1);
            expect(useAppStore.getState().selectedIds.has(1)).toBe(false);
        });

        it('selects all', () => {
            useAppStore.getState().selectAll([1, 2, 3]);
            expect(useAppStore.getState().selectedIds.size).toBe(3);
        });

        it('clears selection', () => {
            useAppStore.getState().selectAll([1, 2, 3]);
            useAppStore.getState().clearSelection();
            expect(useAppStore.getState().selectedIds.size).toBe(0);
        });
    });

    describe('filters', () => {
        it('sets search and resets page', () => {
            useAppStore.getState().setPage(3);
            useAppStore.getState().setSearch('engineer');
            const state = useAppStore.getState();
            expect(state.filters.search).toBe('engineer');
            expect(state.page).toBe(1);
        });

        it('sets status filter', () => {
            useAppStore.getState().setStatusFilter(['pending', 'qualified']);
            expect(useAppStore.getState().filters.status).toEqual(['pending', 'qualified']);
        });

        it('clears all filters', () => {
            useAppStore.getState().setSearch('test');
            useAppStore.getState().setStatusFilter(['error']);
            useAppStore.getState().clearFilters();
            const { filters } = useAppStore.getState();
            expect(filters.search).toBe('');
            expect(filters.status).toEqual([]);
        });

        it('sets score range', () => {
            useAppStore.getState().setScoreRange(50, 90);
            const { filters } = useAppStore.getState();
            expect(filters.score_min).toBe(50);
            expect(filters.score_max).toBe(90);
        });
    });

    describe('sort', () => {
        it('defaults to updated_at desc', () => {
            expect(useAppStore.getState().sort).toEqual({ column: 'updated_at', direction: 'desc' });
        });

        it('sets new sort', () => {
            useAppStore.getState().setSort({ column: 'score', direction: 'asc' });
            expect(useAppStore.getState().sort).toEqual({ column: 'score', direction: 'asc' });
        });

        it('can clear sort', () => {
            useAppStore.getState().setSort(null);
            expect(useAppStore.getState().sort).toBeNull();
        });
    });

    describe('pagination', () => {
        it('defaults to page 1, limit 50', () => {
            expect(useAppStore.getState().page).toBe(1);
            expect(useAppStore.getState().limit).toBe(50);
        });

        it('changes page', () => {
            useAppStore.getState().setPage(5);
            expect(useAppStore.getState().page).toBe(5);
        });

        it('changing limit resets page', () => {
            useAppStore.getState().setPage(5);
            useAppStore.getState().setLimit(100);
            expect(useAppStore.getState().limit).toBe(100);
            expect(useAppStore.getState().page).toBe(1);
        });
    });

    describe('detail drawer', () => {
        it('defaults to null', () => {
            expect(useAppStore.getState().selectedJobId).toBeNull();
        });

        it('selects a job', () => {
            useAppStore.getState().setSelectedJobId(42);
            expect(useAppStore.getState().selectedJobId).toBe(42);
        });

        it('deselects a job', () => {
            useAppStore.getState().setSelectedJobId(42);
            useAppStore.getState().setSelectedJobId(null);
            expect(useAppStore.getState().selectedJobId).toBeNull();
        });
    });
});

describe('useUIStore', () => {
    describe('command palette', () => {
        it('defaults to closed', () => {
            expect(useUIStore.getState().commandPaletteOpen).toBe(false);
        });

        it('toggles open/close', () => {
            useUIStore.getState().toggleCommandPalette();
            expect(useUIStore.getState().commandPaletteOpen).toBe(true);
            useUIStore.getState().toggleCommandPalette();
            expect(useUIStore.getState().commandPaletteOpen).toBe(false);
        });
    });

    describe('toasts', () => {
        it('adds a toast', () => {
            useUIStore.getState().addToast({ type: 'success', message: 'Saved' });
            expect(useUIStore.getState().toasts).toHaveLength(1);
            expect(useUIStore.getState().toasts[0].message).toBe('Saved');
        });

        it('removes a toast by id', () => {
            useUIStore.getState().addToast({ type: 'info', message: 'Info' });
            const id = useUIStore.getState().toasts[0].id;
            useUIStore.getState().removeToast(id);
            expect(useUIStore.getState().toasts).toHaveLength(0);
        });
    });
});
