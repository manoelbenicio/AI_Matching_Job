'use client';

import { useJobStats } from '@/hooks/use-jobs';
import { cn } from '@/lib/utils';
import { SkeletonMetrics } from '@/components/ui/skeleton';

export function MetricsBar() {
    const { data: stats, isLoading } = useJobStats();

    if (isLoading || !stats) {
        return <SkeletonMetrics />;
    }

    const metrics = [
        {
            label: 'Total Jobs',
            value: stats.total,
            color: undefined,
        },
        {
            label: 'Qualified',
            value: stats.by_status.qualified || 0,
            color: 'var(--success)',
        },
        {
            label: 'Enhanced',
            value: stats.by_status.enhanced || 0,
            color: '#a855f7',
        },
        {
            label: 'Avg Score',
            value: stats.avg_score !== null ? `${Math.round(stats.avg_score)}` : '—',
            color: 'var(--accent-primary)',
        },
        {
            label: 'High Score (≥80)',
            value: stats.high_score_count,
            color: 'var(--score-excellent)',
        },
    ];

    return (
        <div className="metrics-bar">
            {metrics.map((m) => (
                <div key={m.label} className="metric-card">
                    <span
                        className="metric-card__value"
                        style={m.color ? { color: m.color } : undefined}
                    >
                        {m.value}
                    </span>
                    <span className="metric-card__label">{m.label}</span>
                </div>
            ))}
        </div>
    );
}
