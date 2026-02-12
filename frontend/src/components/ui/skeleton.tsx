'use client';

import './skeleton.css';

/* ============================================================
   Shimmer Skeleton Components
   Usage:
     <SkeletonRow />         — table row placeholder
     <SkeletonCard />        — kanban card placeholder
     <SkeletonDetail />      — detail panel placeholder
     <SkeletonMetrics />     — metrics bar (5 stat cards)
   ============================================================ */

function Bone({ width = '100%', height = '12px', radius = 'var(--radius-sm)' }: {
    width?: string;
    height?: string;
    radius?: string;
}) {
    return (
        <div
            className="skeleton-bone"
            style={{ width, height, borderRadius: radius }}
            aria-hidden="true"
        />
    );
}

/** Table row — 6 shimmer cells */
export function SkeletonRow() {
    return (
        <div className="skeleton-row" aria-hidden="true">
            <Bone width="60%" height="14px" />
            <Bone width="40%" height="14px" />
            <Bone width="48px" height="24px" radius="var(--radius-full)" />
            <Bone width="72px" height="22px" radius="var(--radius-full)" />
            <Bone width="30%" height="14px" />
            <Bone width="80px" height="14px" />
        </div>
    );
}

/** Multiple table rows */
export function SkeletonTable({ rows = 8 }: { rows?: number }) {
    return (
        <div className="skeleton-table" role="status" aria-label="Loading data">
            {Array.from({ length: rows }, (_, i) => (
                <SkeletonRow key={i} />
            ))}
        </div>
    );
}

/** Kanban card placeholder */
export function SkeletonCard() {
    return (
        <div className="skeleton-card" aria-hidden="true">
            <Bone width="70%" height="14px" />
            <Bone width="50%" height="12px" />
            <div className="skeleton-card__footer">
                <Bone width="48px" height="20px" radius="var(--radius-full)" />
                <Bone width="60px" height="12px" />
            </div>
        </div>
    );
}

/** Detail panel placeholder */
export function SkeletonDetail() {
    return (
        <div className="skeleton-detail" role="status" aria-label="Loading details">
            {/* Title */}
            <Bone width="80%" height="20px" />
            <Bone width="50%" height="14px" />

            {/* Status badge */}
            <Bone width="80px" height="28px" radius="var(--radius-full)" />

            {/* Info grid — 2 cols × 4 rows */}
            <div className="skeleton-detail__grid">
                {Array.from({ length: 8 }, (_, i) => (
                    <div key={i} className="skeleton-detail__field">
                        <Bone width="60px" height="10px" />
                        <Bone width="120px" height="14px" />
                    </div>
                ))}
            </div>

            {/* Description block */}
            <Bone width="100%" height="10px" />
            <Bone width="100%" height="120px" radius="var(--radius-md)" />
        </div>
    );
}

/** Metrics bar — 5 stat cards */
export function SkeletonMetrics() {
    return (
        <div className="skeleton-metrics" role="status" aria-label="Loading metrics">
            {Array.from({ length: 5 }, (_, i) => (
                <div key={i} className="skeleton-metrics__card">
                    <Bone width="48px" height="28px" />
                    <Bone width="80px" height="12px" />
                </div>
            ))}
        </div>
    );
}
