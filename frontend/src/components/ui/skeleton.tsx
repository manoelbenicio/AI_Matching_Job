'use client';

/**
 * Loading Skeleton Components
 * Shimmer-effect placeholders for table rows, kanban cards, detail panel, and metrics bar.
 */

export function SkeletonLine({ width = '80%', height = 14 }: { width?: string; height?: number }) {
    return <div className="skeleton" style={{ width, height }} />;
}

export function SkeletonTableRows({ rows = 8 }: { rows?: number }) {
    return (
        <div className="skeleton-table" role="status" aria-label="Loading table data">
            {Array.from({ length: rows }).map((_, i) => (
                <div key={i} className="skeleton-table__row">
                    <div className="skeleton" style={{ width: 32, height: 32, borderRadius: '50%' }} />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <div className="skeleton skeleton--text" style={{ width: `${60 + Math.random() * 30}%` }} />
                        <div className="skeleton skeleton--text-sm" style={{ width: `${40 + Math.random() * 20}%` }} />
                    </div>
                    <div className="skeleton" style={{ width: 64, height: 24, borderRadius: 12 }} />
                    <div className="skeleton" style={{ width: 48, height: 20 }} />
                </div>
            ))}
            <span className="sr-only">Loading…</span>
        </div>
    );
}

export function SkeletonKanbanCards({ columns = 5, cardsPerColumn = 3 }: { columns?: number; cardsPerColumn?: number }) {
    return (
        <div className="skeleton-kanban" role="status" aria-label="Loading kanban board">
            {Array.from({ length: columns }).map((_, col) => (
                <div key={col} className="skeleton-kanban__column">
                    <div className="skeleton" style={{ width: '60%', height: 16, marginBottom: 12 }} />
                    {Array.from({ length: cardsPerColumn }).map((_, card) => (
                        <div key={card} className="skeleton skeleton--card" />
                    ))}
                </div>
            ))}
            <span className="sr-only">Loading…</span>
        </div>
    );
}

export function SkeletonDetailPanel() {
    return (
        <div className="skeleton-detail" role="status" aria-label="Loading job details">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}>
                <div className="skeleton" style={{ width: '70%', height: 24 }} />
                <div className="skeleton" style={{ width: '50%', height: 16 }} />
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <div className="skeleton" style={{ width: 80, height: 28, borderRadius: 14 }} />
                    <div className="skeleton" style={{ width: 80, height: 28, borderRadius: 14 }} />
                    <div className="skeleton" style={{ width: 80, height: 28, borderRadius: 14 }} />
                </div>
                <div className="skeleton" style={{ width: '100%', height: 1, margin: '8px 0' }} />
                <div className="skeleton skeleton--text" />
                <div className="skeleton skeleton--text" style={{ width: '90%' }} />
                <div className="skeleton skeleton--text" style={{ width: '75%' }} />
                <div className="skeleton skeleton--text-sm" style={{ width: '50%' }} />
            </div>
            <span className="sr-only">Loading…</span>
        </div>
    );
}

export function SkeletonMetricsBar() {
    return (
        <div className="skeleton-metrics" role="status" aria-label="Loading metrics">
            {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="skeleton-metrics__item">
                    <div className="skeleton" style={{ width: 40, height: 28 }} />
                    <div className="skeleton skeleton--text-sm" style={{ width: 60 }} />
                </div>
            ))}
            <span className="sr-only">Loading…</span>
        </div>
    );
}
