import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { JobFilters, ViewMode, SortConfig } from '@/lib/types';

// === Main application store ===
interface AppState {
    // View
    viewMode: ViewMode;
    setViewMode: (mode: ViewMode) => void;

    // Selection
    selectedIds: Set<number>;
    toggleSelection: (id: number) => void;
    selectAll: (ids: number[]) => void;
    clearSelection: () => void;

    // Filters
    filters: JobFilters;
    setSearch: (search: string) => void;
    setStatusFilter: (statuses: JobFilters['status']) => void;
    setWorkTypeFilter: (types: string[]) => void;
    setScoreRange: (min: number | null, max: number | null) => void;
    clearFilters: () => void;

    // Sorting
    sort: SortConfig | null;
    setSort: (sort: SortConfig | null) => void;

    // Pagination
    page: number;
    limit: number;
    setPage: (page: number) => void;
    setLimit: (limit: number) => void;

    // Detail drawer
    selectedJobId: number | null;
    setSelectedJobId: (id: number | null) => void;
}

const DEFAULT_FILTERS: JobFilters = {
    search: '',
    status: [],
    work_type: [],
    score_min: null,
    score_max: null,
};

export const useAppStore = create<AppState>()(
    persist(
        (set) => ({
            // View
            viewMode: 'table',
            setViewMode: (mode) => set({ viewMode: mode }),

            // Selection (not persisted)
            selectedIds: new Set(),
            toggleSelection: (id) =>
                set((state) => {
                    const next = new Set(state.selectedIds);
                    if (next.has(id)) next.delete(id);
                    else next.add(id);
                    return { selectedIds: next };
                }),
            selectAll: (ids) => set({ selectedIds: new Set(ids) }),
            clearSelection: () => set({ selectedIds: new Set() }),

            // Filters (not persisted)
            filters: { ...DEFAULT_FILTERS },
            setSearch: (search) =>
                set((state) => ({ filters: { ...state.filters, search }, page: 1 })),
            setStatusFilter: (status) =>
                set((state) => ({ filters: { ...state.filters, status }, page: 1 })),
            setWorkTypeFilter: (work_type) =>
                set((state) => ({ filters: { ...state.filters, work_type }, page: 1 })),
            setScoreRange: (score_min, score_max) =>
                set((state) => ({ filters: { ...state.filters, score_min, score_max }, page: 1 })),
            clearFilters: () => set({ filters: { ...DEFAULT_FILTERS }, page: 1 }),

            // Sorting
            sort: { column: 'updated_at', direction: 'desc' },
            setSort: (sort) => set({ sort }),

            // Pagination
            page: 1,
            limit: 50,
            setPage: (page) => set({ page }),
            setLimit: (limit) => set({ limit, page: 1 }),

            // Detail
            selectedJobId: null,
            setSelectedJobId: (id) => set({ selectedJobId: id }),
        }),
        {
            name: 'ai-job-matcher-preferences',
            partialize: (state) => ({
                viewMode: state.viewMode,
                sort: state.sort,
                limit: state.limit,
            }),
        }
    )
);

// === UI Store (toasts, modals, command palette) ===
interface Toast {
    id: string;
    type: 'success' | 'error' | 'info' | 'warning';
    message: string;
    duration?: number;
}

interface UIState {
    // Command palette
    commandPaletteOpen: boolean;
    toggleCommandPalette: () => void;
    setCommandPaletteOpen: (open: boolean) => void;

    // Toasts
    toasts: Toast[];
    addToast: (toast: Omit<Toast, 'id'>) => void;
    removeToast: (id: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
    commandPaletteOpen: false,
    toggleCommandPalette: () =>
        set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),
    setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

    toasts: [],
    addToast: (toast) => {
        const id = Math.random().toString(36).substring(2, 9);
        const duration = toast.duration ?? 4000;
        set((state) => ({
            toasts: [...state.toasts, { ...toast, id, duration }].slice(-5), // max 5 visible
        }));
        setTimeout(() => {
            set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
        }, duration);
    },
    removeToast: (id) =>
        set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
