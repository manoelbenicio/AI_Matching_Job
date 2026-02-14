import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ScoreBreakdownTab } from '@/components/detail-panel/score-breakdown-tab';
import type { ScoreBreakdown } from '@/lib/types';

describe('ScoreBreakdownTab', () => {
    it('renders new schema fields (strong/weak)', () => {
        const breakdown: ScoreBreakdown = {
            overall_score: 84,
            interview_probability: 'HIGH',
            model_used: 'OpenAI (gpt-4o-mini)',
            sections: [
                {
                    dimension: 'Technical Skills',
                    score: 90,
                    strong: ['Python'],
                    weak: ['Kubernetes'],
                    recommendations: ['Add k8s project'],
                },
            ],
            key_risks: ['No enterprise k8s'],
            cv_enhancement_priority: ['Leadership'],
            scored_at: '2026-02-12T00:00:00Z',
        };

        render(<ScoreBreakdownTab breakdown={breakdown} />);
        expect(screen.getByText(/Overall Match/i)).toBeInTheDocument();
        expect(screen.getByText(/OpenAI \(gpt-4o-mini\)/i)).toBeInTheDocument();
        expect(screen.getByText(/HIGH Chance/i)).toBeInTheDocument();
        expect(screen.getByText(/Technical Skills/i)).toBeInTheDocument();
    });

    it('renders legacy aliases (strong_points/weak_points)', () => {
        const breakdown: ScoreBreakdown = {
            overall_score: 72,
            interview_probability: 'MEDIUM',
            sections: [
                {
                    dimension: 'Experience Level',
                    score: 70,
                    strong_points: ['8 years experience'],
                    weak_points: ['No direct FinTech'],
                    recommendations: ['Add regulated domain examples'],
                },
            ],
            cv_enhancement_priorities: ['Industry exposure'],
        };

        render(<ScoreBreakdownTab breakdown={breakdown} />);
        expect(screen.getByText(/Experience Level/i)).toBeInTheDocument();
        expect(screen.getByText(/MEDIUM Chance/i)).toBeInTheDocument();
        expect(screen.getByText(/Industry exposure/i)).toBeInTheDocument();
    });

    it('renders compare mode metadata', () => {
        const breakdown: ScoreBreakdown = {
            overall_score: 80,
            sections: [],
            compare_mode: true,
            best_provider: 'gemini',
            results: {
                openai: { overall_score: 76 },
                gemini: { overall_score: 80 },
            },
        };

        render(<ScoreBreakdownTab breakdown={breakdown} />);
        expect(screen.getByText(/Provider Compare/i)).toBeInTheDocument();
        expect(screen.getByText(/Best: GEMINI/i)).toBeInTheDocument();
        expect(screen.getByText(/Providers: openai, gemini/i)).toBeInTheDocument();
    });
});
