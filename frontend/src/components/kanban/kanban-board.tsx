'use client';

import { useMemo, useCallback, useState, useRef, useEffect, memo } from 'react';
import {
    DndContext,
    closestCenter,
    PointerSensor,
    KeyboardSensor,
    useSensor,
    useSensors,
    type DragEndEvent,
    type DragStartEvent,
    DragOverlay,
} from '@dnd-kit/core';
import {
    SortableContext,
    verticalListSortingStrategy,
    useSortable,
    sortableKeyboardCoordinates,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useJobs, useUpdateJob } from '@/hooks/use-jobs';
import { useAppStore } from '@/stores/app-store';
import { truncate, formatScore } from '@/lib/utils';
import { PIPELINE_STAGES, getStatusLabel } from '@/lib/types';
import type { Job, JobStatus } from '@/lib/types';
import { SkeletonCard } from '@/components/ui/skeleton';

// ──────────────────────────────────────────────────
// Swimlane types & grouping
// ──────────────────────────────────────────────────
type SwimLaneMode = 'none' | 'company' | 'score';

function getScoreBucket(score: number | null): string {
    if (score === null) return 'No Score';
    if (score >= 90) return '90–100 (Excellent)';
    if (score >= 80) return '80–89 (Great)';
    if (score >= 70) return '70–79 (Good)';
    if (score >= 50) return '50–69 (Partial)';
    return '0–49 (Weak)';
}

function groupBySwimlane(jobs: Job[], mode: SwimLaneMode): Record<string, Job[]> {
    if (mode === 'none') return { '': jobs };
    const groups: Record<string, Job[]> = {};
    for (const job of jobs) {
        const key = mode === 'company'
            ? (job.company_name || 'Unknown')
            : getScoreBucket(job.score);
        if (!groups[key]) groups[key] = [];
        groups[key].push(job);
    }
    // Sort group keys
    const sortedKeys = Object.keys(groups).sort((a, b) => {
        if (mode === 'score') {
            // Reverse to show highest scores first
            return b.localeCompare(a);
        }
        return a.localeCompare(b);
    });
    const sorted: Record<string, Job[]> = {};
    for (const k of sortedKeys) sorted[k] = groups[k];
    return sorted;
}

// ──────────────────────────────────────────────────
// Accessibility announcements for keyboard DnD
// ──────────────────────────────────────────────────
function getDragAnnouncement(event: DragStartEvent): string {
    return `Picked up card. Use arrow keys to move between columns, then press Space or Enter to drop.`;
}
function getDropAnnouncement(event: DragEndEvent, allJobs: Job[]): string {
    const { active, over } = event;
    if (!over) return `Card dropped — no change.`;
    const job = allJobs.find(j => j.id === active.id);
    const targetStage = PIPELINE_STAGES.find(s => s.id === over.id);
    if (job && targetStage) {
        return `Moved "${job.job_title}" to ${targetStage.name}.`;
    }
    return `Card dropped.`;
}

// ══════════════════════════════════════════════════
// Main KanbanBoard component
// ══════════════════════════════════════════════════
export function KanbanBoard() {
    const { data: response, isLoading } = useJobs();
    const updateJob = useUpdateJob();
    const setSelectedJobId = useAppStore((s) => s.setSelectedJobId);
    const [swimlaneMode, setSwimLaneMode] = useState<SwimLaneMode>('none');
    const [activeId, setActiveId] = useState<number | null>(null);
    const [announcement, setAnnouncement] = useState('');

    // Sensors: pointer + keyboard
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 5 },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // All jobs flat
    const allJobs = useMemo(() => response?.data || [], [response?.data]);

    // Group jobs by status → columns
    const columns = useMemo(() => {
        const grouped: Record<string, Job[]> = {};
        for (const stage of PIPELINE_STAGES) {
            grouped[stage.id] = [];
        }
        for (const job of allJobs) {
            if (grouped[job.status]) {
                grouped[job.status].push(job);
            }
        }
        return grouped;
    }, [allJobs]);

    // Active drag job (for overlay)
    const activeJob = useMemo(
        () => (activeId != null ? allJobs.find((j) => j.id === activeId) ?? null : null),
        [activeId, allJobs]
    );

    const handleDragStart = useCallback((event: DragStartEvent) => {
        setActiveId(event.active.id as number);
        setAnnouncement(getDragAnnouncement(event));
    }, []);

    const handleDragEnd = useCallback(
        (event: DragEndEvent) => {
            setActiveId(null);
            const { active, over } = event;
            if (!over) {
                setAnnouncement('Card dropped — no change.');
                return;
            }

            const jobId = active.id as number;
            const targetStatus = over.id as JobStatus;

            const job = allJobs.find((j) => j.id === jobId);
            if (!job || job.status === targetStatus) {
                setAnnouncement('Card dropped — no change.');
                return;
            }

            updateJob.mutate({
                id: jobId,
                data: { status: targetStatus, version: job.version },
            });
            setAnnouncement(getDropAnnouncement(event, allJobs));
        },
        [allJobs, updateJob]
    );

    const handleStatusChange = useCallback(
        (jobId: number, newStatus: JobStatus, version: number) => {
            updateJob.mutate({
                id: jobId,
                data: { status: newStatus, version },
            });
        },
        [updateJob]
    );

    if (isLoading) {
        return (
            <div className="kanban-board">
                {PIPELINE_STAGES.filter(s => ['pending', 'qualified', 'enhanced', 'low_score'].includes(s.id)).map((stage) => (
                    <div key={stage.id} className="kanban-column">
                        <div className="kanban-column__header">
                            <div className="kanban-column__title">{stage.name}</div>
                        </div>
                        <div className="kanban-column__body">
                            {Array.from({ length: 3 }).map((_, i) => (
                                <SkeletonCard key={i} />
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    // Only show columns that have jobs or are primary stages
    const visibleStages = PIPELINE_STAGES.filter(
        (s) => ['pending', 'processing', 'qualified', 'enhanced', 'low_score'].includes(s.id) || (columns[s.id]?.length ?? 0) > 0
    );

    return (
        <div className="kanban-wrapper">
            {/* ── Swimlanes Toolbar ── */}
            <div className="kanban-toolbar">
                <div className="kanban-toolbar__label">Group by:</div>
                <div className="kanban-toolbar__btns">
                    {([
                        { value: 'none', label: 'None' },
                        { value: 'company', label: 'Company' },
                        { value: 'score', label: 'Score Range' },
                    ] as const).map((opt) => (
                        <button
                            key={opt.value}
                            className={`kanban-toolbar__btn ${swimlaneMode === opt.value ? 'kanban-toolbar__btn--active' : ''}`}
                            onClick={() => setSwimLaneMode(opt.value)}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
                <div className="kanban-toolbar__hint">
                    Press <kbd>Space</kbd> on a card to grab, <kbd>←</kbd> <kbd>→</kbd> to move, <kbd>Space</kbd> to drop
                </div>
            </div>

            {/* ── Screen-reader announcements ── */}
            <div
                role="status"
                aria-live="assertive"
                aria-atomic="true"
                className="sr-only"
            >
                {announcement}
            </div>

            <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                accessibility={{
                    announcements: {
                        onDragStart: () => 'Picked up. Use arrow keys to move, Space to drop.',
                        onDragOver: ({ over }) => {
                            if (!over) return 'Not over a droppable area.';
                            const stage = PIPELINE_STAGES.find(s => s.id === over.id);
                            return stage ? `Over ${stage.name} column.` : 'Over a droppable area.';
                        },
                        onDragEnd: ({ active, over }) => {
                            if (!over) return 'Dropped — no change.';
                            const job = allJobs.find(j => j.id === active.id);
                            const stage = PIPELINE_STAGES.find(s => s.id === over.id);
                            if (job && stage) return `Moved "${job.job_title}" to ${stage.name}.`;
                            return 'Dropped.';
                        },
                        onDragCancel: () => 'Drag cancelled.',
                    },
                }}
            >
                {swimlaneMode === 'none' ? (
                    /* ── Regular (flat) board ── */
                    <div className="kanban-board">
                        {visibleStages.map((stage) => (
                            <KanbanColumn
                                key={stage.id}
                                stage={stage}
                                jobs={columns[stage.id] || []}
                                onCardClick={(job) => setSelectedJobId(job.id)}
                                onStatusChange={handleStatusChange}
                                isDragActive={activeId != null}
                            />
                        ))}
                    </div>
                ) : (
                    /* ── Swimlane board ── */
                    <div className="kanban-swimlanes">
                        {Object.entries(groupBySwimlane(allJobs, swimlaneMode)).map(
                            ([lane, laneJobs]) => {
                                // Group lane jobs by status
                                const laneColumns: Record<string, Job[]> = {};
                                for (const s of visibleStages) laneColumns[s.id] = [];
                                for (const j of laneJobs) {
                                    if (laneColumns[j.status]) laneColumns[j.status].push(j);
                                }
                                return (
                                    <div key={lane} className="kanban-swimlane">
                                        <div className="kanban-swimlane__header">
                                            <span className="kanban-swimlane__name">{lane}</span>
                                            <span className="kanban-swimlane__count">{laneJobs.length} jobs</span>
                                        </div>
                                        <div className="kanban-board kanban-board--in-swimlane">
                                            {visibleStages.map((stage) => (
                                                <KanbanColumn
                                                    key={`${lane}-${stage.id}`}
                                                    stage={stage}
                                                    jobs={laneColumns[stage.id] || []}
                                                    onCardClick={(job) => setSelectedJobId(job.id)}
                                                    onStatusChange={handleStatusChange}
                                                    isDragActive={activeId != null}
                                                    compact
                                                />
                                            ))}
                                        </div>
                                    </div>
                                );
                            }
                        )}
                    </div>
                )}

                {/* ── Drag overlay (ghost card while dragging) ── */}
                <DragOverlay>
                    {activeJob ? (
                        <div className="kanban-card kanban-card--overlay">
                            <div className="kanban-card__header">
                                <div className="kanban-card__title">{truncate(activeJob.job_title, 50)}</div>
                            </div>
                            <div className="kanban-card__company">{activeJob.company_name}</div>
                        </div>
                    ) : null}
                </DragOverlay>
            </DndContext>
        </div>
    );
}

// ══════════════════════════════════════════════════
// KanbanColumn
// ══════════════════════════════════════════════════
function KanbanColumn({
    stage,
    jobs,
    onCardClick,
    onStatusChange,
    compact = false,
    isDragActive = false,
}: {
    stage: (typeof PIPELINE_STAGES)[number];
    jobs: Job[];
    onCardClick: (job: Job) => void;
    onStatusChange: (jobId: number, newStatus: JobStatus, version: number) => void;
    compact?: boolean;
    isDragActive?: boolean;
}) {
    const { setNodeRef } = useSortable({
        id: stage.id,
        data: { type: 'column' },
    });

    return (
        <div className={`kanban-column ${compact ? 'kanban-column--compact' : ''}`} ref={setNodeRef} aria-dropeffect={isDragActive ? 'move' : 'none'}>
            <div className="kanban-column__header">
                <div className="kanban-column__title">
                    <span
                        style={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            background: stage.color,
                            display: 'inline-block',
                        }}
                    />
                    {stage.name}
                    <span className="kanban-column__count">{jobs.length}</span>
                </div>
            </div>
            <SortableContext items={jobs.map((j) => j.id)} strategy={verticalListSortingStrategy}>
                <div className="kanban-column__body" data-droppable-id={stage.id}>
                    {jobs.length === 0 ? (
                        <div style={{
                            padding: compact ? 'var(--space-3) var(--space-2)' : 'var(--space-6) var(--space-4)',
                            textAlign: 'center',
                            color: 'var(--text-muted)',
                            fontSize: 'var(--fs-xs)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px dashed var(--border-default)',
                        }}>
                            Drop here
                        </div>
                    ) : (
                        jobs.map((job) => (
                            <KanbanCard
                                key={job.id}
                                job={job}
                                currentStatus={stage.id as JobStatus}
                                onClick={() => onCardClick(job)}
                                onStatusChange={onStatusChange}
                                compact={compact}
                            />
                        ))
                    )}
                </div>
            </SortableContext>
        </div>
    );
}

// ══════════════════════════════════════════════════
// KanbanCard
// ══════════════════════════════════════════════════
const KanbanCard = memo(function KanbanCard({
    job,
    currentStatus,
    onClick,
    onStatusChange,
    compact = false,
}: {
    job: Job;
    currentStatus: JobStatus;
    onClick: () => void;
    onStatusChange: (jobId: number, newStatus: JobStatus, version: number) => void;
    compact?: boolean;
}) {
    const selectedJobId = useAppStore((s) => s.selectedJobId);
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: job.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    const { text: scoreText, className: scoreClass } = formatScore(job.score);

    // Close menu on outside click
    useEffect(() => {
        if (!menuOpen) return;
        const handler = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [menuOpen]);

    // Available status transitions (exclude current)
    const moveTargets = PIPELINE_STAGES.filter(
        (s) => s.id !== currentStatus && ['pending', 'qualified', 'enhanced', 'low_score', 'rejected', 'applied'].includes(s.id)
    );

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            className={`kanban-card ${isDragging ? 'kanban-card--dragging' : ''} ${selectedJobId === job.id ? 'kanban-card--focused' : ''} ${compact ? 'kanban-card--compact' : ''}`}
            onClick={onClick}
            role="button"
            tabIndex={0}
            aria-roledescription="sortable card"
            aria-grabbed={isDragging}
            aria-label={`${job.job_title} at ${job.company_name}. Score: ${scoreText}. Press Space to grab and move.`}
        >
            <div className="kanban-card__header">
                <div className="kanban-card__title">{truncate(job.job_title, compact ? 35 : 50)}</div>
                <button
                    className="kanban-card__menu-btn"
                    onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpen((v) => !v);
                    }}
                    aria-label="Card actions"
                >
                    ⋯
                </button>
            </div>

            {/* Quick actions dropdown */}
            {menuOpen && (
                <div className="kanban-card__menu" ref={menuRef} onClick={(e) => e.stopPropagation()}>
                    <button
                        className="kanban-card__menu-item"
                        onClick={() => { onClick(); setMenuOpen(false); }}
                    >
                        📋 View Details
                    </button>
                    {job.job_url && (
                        <button
                            className="kanban-card__menu-item"
                            onClick={() => {
                                window.open(job.job_url!, '_blank');
                                setMenuOpen(false);
                            }}
                        >
                            🔗 Open Link
                        </button>
                    )}
                    <div className="kanban-card__menu-divider" />
                    <div className="kanban-card__menu-label">Move to…</div>
                    {moveTargets.map((stage) => (
                        <button
                            key={stage.id}
                            className="kanban-card__menu-item"
                            onClick={() => {
                                onStatusChange(job.id, stage.id as JobStatus, job.version);
                                setMenuOpen(false);
                            }}
                        >
                            <span
                                style={{
                                    width: 6,
                                    height: 6,
                                    borderRadius: '50%',
                                    background: stage.color,
                                    display: 'inline-block',
                                    marginRight: 6,
                                }}
                            />
                            {stage.name}
                        </button>
                    ))}
                </div>
            )}

            <div className="kanban-card__company">{job.company_name}</div>
            {!compact && (
                <div className="kanban-card__footer">
                    <span className={scoreClass} style={{ fontSize: 'var(--fs-xs)' }}>
                        {scoreText !== '—' ? `Score: ${scoreText}` : ''}
                    </span>
                    {job.work_type && (
                        <span style={{
                            fontSize: 'var(--fs-xs)',
                            color: 'var(--text-muted)',
                            background: 'var(--bg-elevated)',
                            padding: '1px 6px',
                            borderRadius: 'var(--radius-full)',
                        }}>
                            {job.work_type}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
});
