import { describe, it, expect } from 'vitest';
import { formatDate, formatRelativeTime, formatScore, truncate, cn, buildSearchParams } from '@/lib/utils';

describe('formatDate', () => {
    it('returns dash for null', () => {
        expect(formatDate(null)).toBe('—');
    });

    it('formats a valid date', () => {
        const result = formatDate('2026-01-15T12:00:00Z');
        expect(result).toMatch(/Jan/);
        expect(result).toMatch(/15/);
        expect(result).toMatch(/2026/);
    });
});

describe('formatRelativeTime', () => {
    it('returns "just now" for very recent dates', () => {
        const now = new Date().toISOString();
        expect(formatRelativeTime(now)).toBe('just now');
    });
});

describe('formatScore', () => {
    it('returns dash for null score', () => {
        const result = formatScore(null);
        expect(result.text).toBe('—');
        expect(result.className).toBe('');
    });

    it('returns score text and class for valid score', () => {
        const result = formatScore(85);
        expect(result.text).toBe('85');
        expect(result.className).toContain('score');
    });

    it('handles zero score', () => {
        const result = formatScore(0);
        expect(result.text).toBe('0');
        expect(result.className).toContain('score');
    });
});

describe('truncate', () => {
    it('returns dash for null', () => {
        expect(truncate(null)).toBe('—');
    });

    it('returns full text if under limit', () => {
        expect(truncate('Hello', 10)).toBe('Hello');
    });

    it('truncates long text with ellipsis', () => {
        const long = 'A'.repeat(60);
        const result = truncate(long, 50);
        expect(result.length).toBe(51); // 50 chars + ellipsis
        expect(result).toContain('…');
    });
});

describe('cn', () => {
    it('joins truthy classes', () => {
        expect(cn('a', 'b', 'c')).toBe('a b c');
    });

    it('filters falsy values', () => {
        expect(cn('a', false, null, undefined, 'b')).toBe('a b');
    });

    it('returns empty string for no truthy values', () => {
        expect(cn(false, null, undefined)).toBe('');
    });
});

describe('buildSearchParams', () => {
    const emptyFilters = {
        search: '',
        status: [],
        work_type: [],
        score_min: null,
        score_max: null,
    };

    it('includes page and limit', () => {
        const params = buildSearchParams(emptyFilters, null, 1, 50);
        expect(params.get('page')).toBe('1');
        expect(params.get('limit')).toBe('50');
    });

    it('includes search when set', () => {
        const params = buildSearchParams({ ...emptyFilters, search: 'engineer' }, null);
        expect(params.get('search')).toBe('engineer');
    });

    it('includes sort when set', () => {
        const params = buildSearchParams(emptyFilters, { column: 'score', direction: 'desc' });
        expect(params.get('sort')).toBe('score:desc');
    });

    it('includes status filter', () => {
        const filters = { ...emptyFilters, status: ['pending' as const, 'qualified' as const] };
        const params = buildSearchParams(filters, null);
        expect(params.get('status')).toBe('pending,qualified');
    });

    it('includes score_min when set', () => {
        const params = buildSearchParams({ ...emptyFilters, score_min: 50 }, null);
        expect(params.get('score_min')).toBe('50');
    });
});
