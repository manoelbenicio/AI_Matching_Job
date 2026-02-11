'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * Preference persistence hook — saves/restores user preferences to localStorage.
 * Supports: column visibility, table density, view mode, and custom settings.
 */

const STORAGE_KEY = 'ai-job-matcher-user-prefs';

interface UserPreferences {
    // Table
    columnVisibility: Record<string, boolean>;
    tableDensity: 'compact' | 'comfortable' | 'spacious';
    pageSize: number;

    // Kanban
    kanbanGroupBy: 'status' | 'work_type' | 'seniority';
    showSwimLanes: boolean;
    compactCards: boolean;

    // View
    defaultView: 'table' | 'kanban' | 'split';

    // Sidebar
    detailPanelWidth: number;
}

const DEFAULT_PREFERENCES: UserPreferences = {
    columnVisibility: {},
    tableDensity: 'comfortable',
    pageSize: 50,
    kanbanGroupBy: 'status',
    showSwimLanes: false,
    compactCards: false,
    defaultView: 'table',
    detailPanelWidth: 480,
};

function loadFromStorage(): UserPreferences {
    if (typeof window === 'undefined') return DEFAULT_PREFERENCES;
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return DEFAULT_PREFERENCES;
        return { ...DEFAULT_PREFERENCES, ...JSON.parse(raw) };
    } catch {
        return DEFAULT_PREFERENCES;
    }
}

function saveToStorage(prefs: UserPreferences): void {
    if (typeof window === 'undefined') return;
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch {
        // localStorage full or unavailable — silently ignore
    }
}

export function usePreferences() {
    const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);
    const [loaded, setLoaded] = useState(false);

    // Load from localStorage on mount (client only)
    useEffect(() => {
        setPreferences(loadFromStorage());
        setLoaded(true);
    }, []);

    // Save whenever preferences change (after initial load)
    useEffect(() => {
        if (loaded) {
            saveToStorage(preferences);
        }
    }, [preferences, loaded]);

    const updatePreference = useCallback(<K extends keyof UserPreferences>(
        key: K,
        value: UserPreferences[K],
    ) => {
        setPreferences((prev) => ({ ...prev, [key]: value }));
    }, []);

    const resetPreferences = useCallback(() => {
        setPreferences(DEFAULT_PREFERENCES);
        localStorage.removeItem(STORAGE_KEY);
    }, []);

    const toggleColumnVisibility = useCallback((columnId: string) => {
        setPreferences((prev) => ({
            ...prev,
            columnVisibility: {
                ...prev.columnVisibility,
                [columnId]: !prev.columnVisibility[columnId],
            },
        }));
    }, []);

    return {
        preferences,
        loaded,
        updatePreference,
        resetPreferences,
        toggleColumnVisibility,
    };
}
