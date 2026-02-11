import { getScoreClass } from './types';

/**
 * Format a date string to a human-readable format.
 */
export function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
}

/**
 * Format a date string to relative time (e.g., "2 hours ago").
 */
export function formatRelativeTime(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHr / 24);

    if (diffSec < 60) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;
    return formatDate(dateStr);
}

/**
 * Format a score with appropriate styling class.
 */
export function formatScore(score: number | null): { text: string; className: string } {
    if (score === null) return { text: '—', className: '' };
    return { text: `${score}`, className: `score ${getScoreClass(score)}` };
}

/**
 * Truncate text to a maximum length.
 */
export function truncate(text: string | null, maxLength: number = 50): string {
    if (!text) return '—';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '…';
}

/**
 * Build URLSearchParams from filter state.
 */
export function buildSearchParams(
    filters: import('./types').JobFilters,
    sort: import('./types').SortConfig | null,
    page: number = 1,
    limit: number = 50
): URLSearchParams {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('limit', String(limit));

    if (filters.search) params.set('search', filters.search);
    if (filters.status.length > 0) params.set('status', filters.status.join(','));
    if (filters.work_type.length > 0) params.set('work_type', filters.work_type.join(','));
    if (filters.score_min !== null) params.set('score_min', String(filters.score_min));
    if (filters.score_max !== null) params.set('score_max', String(filters.score_max));
    if (sort) params.set('sort', `${sort.column}:${sort.direction}`);

    return params;
}

/**
 * Debounce a value.
 */
export function cn(...classes: (string | false | null | undefined)[]): string {
    return classes.filter(Boolean).join(' ');
}
