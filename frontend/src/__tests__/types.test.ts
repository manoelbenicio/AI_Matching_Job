import { describe, it, expect } from 'vitest';
import { getScoreClass, getStatusLabel, PIPELINE_STAGES } from '@/lib/types';

describe('getScoreClass', () => {
    it('returns empty for null', () => {
        expect(getScoreClass(null)).toBe('');
    });

    it('returns excellent for 90+', () => {
        expect(getScoreClass(95)).toBe('score--excellent');
        expect(getScoreClass(90)).toBe('score--excellent');
    });

    it('returns great for 80-89', () => {
        expect(getScoreClass(85)).toBe('score--great');
        expect(getScoreClass(80)).toBe('score--great');
    });

    it('returns good for 70-79', () => {
        expect(getScoreClass(75)).toBe('score--good');
        expect(getScoreClass(70)).toBe('score--good');
    });

    it('returns partial for 50-69', () => {
        expect(getScoreClass(60)).toBe('score--partial');
        expect(getScoreClass(50)).toBe('score--partial');
    });

    it('returns weak for below 50', () => {
        expect(getScoreClass(30)).toBe('score--weak');
        expect(getScoreClass(0)).toBe('score--weak');
    });
});

describe('getStatusLabel', () => {
    it('maps all statuses correctly', () => {
        expect(getStatusLabel('pending')).toBe('Pending');
        expect(getStatusLabel('processing')).toBe('Processing');
        expect(getStatusLabel('qualified')).toBe('Qualified');
        expect(getStatusLabel('enhanced')).toBe('Enhanced');
        expect(getStatusLabel('low_score')).toBe('Low Score');
        expect(getStatusLabel('error')).toBe('Error');
        expect(getStatusLabel('skipped')).toBe('Skipped');
    });
});

describe('PIPELINE_STAGES', () => {
    it('has 7 stages', () => {
        expect(PIPELINE_STAGES).toHaveLength(7);
    });

    it('stages are ordered sequentially', () => {
        for (let i = 0; i < PIPELINE_STAGES.length; i++) {
            expect(PIPELINE_STAGES[i].order).toBe(i);
        }
    });

    it('all stages have required fields', () => {
        for (const stage of PIPELINE_STAGES) {
            expect(stage.id).toBeTruthy();
            expect(stage.name).toBeTruthy();
            expect(stage.color).toMatch(/^#[0-9a-f]{6}$/i);
        }
    });
});
