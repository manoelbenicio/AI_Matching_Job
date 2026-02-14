'use client';

import { useEffect } from 'react';
import { useJobStats } from '@/hooks/use-jobs';
import { cn } from '@/lib/utils';
import { SkeletonMetrics } from '@/components/ui/skeleton';
import { useAppStore } from '@/stores/app-store';

export function MetricsBar() {
    const { data: stats, isLoading, refetch } = useJobStats();
    const {
        setStatusFilter,
        setScoreRange,
        clearFilters,
        setViewMode,
        dataRefreshVersion,
    } = useAppStore();
    const qualificationThreshold = stats?.qualification_threshold ?? 80;

    useEffect(() => {
        if (dataRefreshVersion > 0) {
            refetch();
        }
    }, [dataRefreshVersion, refetch]);

    if (isLoading || !stats) {
        return <SkeletonMetrics />;
    }

    const metrics = [
        {
            label: 'Total Jobs',
            value: stats.total,
            color: undefined,
            onClick: () => {
                clearFilters();
                setViewMode('table');
            },
        },
        {
            label: 'Qualified',
            value: stats.by_status.qualified || 0,
            color: 'var(--success)',
            onClick: () => {
                clearFilters();
                setStatusFilter(['qualified']);
                setViewMode('table');
            },
        },
        {
            label: 'Pending',
            value: stats.by_status.Pending || stats.by_status.pending || 0,
            color: '#eab308',
            onClick: () => {
                clearFilters();
                setStatusFilter(['pending']);
                setViewMode('table');
            },
        },
        {
            label: 'Scored',
            value: stats.by_status.Scored || stats.by_status.scored || 0,
            color: '#22c55e',
            onClick: () => {
                clearFilters();
                setStatusFilter(['scored']);
                setViewMode('table');
            },
        },
        {
            label: 'Avg Score',
            value: stats.avg_score !== null ? `${Math.round(stats.avg_score)}` : '—',
            color: 'var(--accent-primary)',
            onClick: undefined, // No filtering for average
        },
        {
            label: `High Score (≥${qualificationThreshold})`,
            value: stats.high_score_count,
            color: 'var(--score-excellent)',
            onClick: () => {
                clearFilters();
                setScoreRange(qualificationThreshold, null);
                setViewMode('table');
            },
        },
    ];

    return (
        <div className="metrics-bar">
            {metrics.map((m) => (
                <div
                    key={m.label}
                    className={cn('metric-card', m.onClick && 'metric-card--clickable')}
                    onClick={m.onClick}
                    role={m.onClick ? 'button' : undefined}
                    tabIndex={m.onClick ? 0 : undefined}
                    onKeyDown={m.onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); m.onClick!(); } } : undefined}
                    title={m.onClick ? `Click to filter by ${m.label}` : undefined}
                >
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
