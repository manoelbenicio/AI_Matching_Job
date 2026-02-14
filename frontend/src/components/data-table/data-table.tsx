'use client';

import { useMemo, useState, useCallback, useRef } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    flexRender,
    type ColumnDef,
    type SortingState,
} from '@tanstack/react-table';
import { useJobs, useUpdateJob } from '@/hooks/use-jobs';
import { useAppStore } from '@/stores/app-store';
import { useDebounce } from '@/hooks/use-debounce';
import { formatDate, formatScore, truncate, cn } from '@/lib/utils';
import { SkeletonTable } from '@/components/ui/skeleton';
import { getStatusLabel } from '@/lib/types';
import type { Job, JobStatus } from '@/lib/types';
import { useVirtualizer } from '@tanstack/react-virtual';
import { api } from '@/lib/api';

const STATUS_OPTIONS: JobStatus[] = ['pending', 'processing', 'qualified', 'enhanced', 'scored', 'low_score', 'error', 'skipped'];
const ROW_HEIGHT = 48;
const VIRTUAL_THRESHOLD = 50; // virtualize when more rows than this

export function DataTable() {
    const {
        filters, setSearch, setStatusFilter,
        sort, setSort, page, setPage, limit,
        selectedIds, toggleSelection, selectAll, clearSelection,
        selectedJobId, setSelectedJobId,
        openAnalysis,
    } = useAppStore();
    const { data: response, isLoading } = useJobs();
    const updateJob = useUpdateJob();

    const [localSearch, setLocalSearch] = useState(filters.search);
    const debouncedSearch = useDebounce(localSearch, 300);

    // Sync debounced search to store
    useMemo(() => {
        if (debouncedSearch !== filters.search) {
            setSearch(debouncedSearch);
        }
    }, [debouncedSearch, filters.search, setSearch]);

    // TanStack sorting state
    const [sorting, setSorting] = useState<SortingState>(
        sort ? [{ id: sort.column, desc: sort.direction === 'desc' }] : []
    );

    const handleSortingChange = useCallback(
        (updater: SortingState | ((prev: SortingState) => SortingState)) => {
            const newSorting = typeof updater === 'function' ? updater(sorting) : updater;
            setSorting(newSorting);
            if (newSorting.length > 0) {
                setSort({ column: newSorting[0].id, direction: newSorting[0].desc ? 'desc' : 'asc' });
            } else {
                setSort(null);
            }
        },
        [sorting, setSort]
    );

    // Inline status change
    const handleStatusChange = useCallback(
        (job: Job, newStatus: JobStatus) => {
            updateJob.mutate({ id: job.id, data: { status: newStatus, version: job.version } });
        },
        [updateJob]
    );

    // Column definitions
    const columns = useMemo<ColumnDef<Job>[]>(
        () => [
            {
                id: 'select',
                header: ({ table }) => (
                    <input
                        type="checkbox"
                        checked={table.getIsAllPageRowsSelected()}
                        onChange={(e) => {
                            table.toggleAllPageRowsSelected(e.target.checked);
                            if (e.target.checked && response?.data) {
                                selectAll(response.data.map((j) => j.id));
                            } else {
                                clearSelection();
                            }
                        }}
                        aria-label="Select all"
                    />
                ),
                cell: ({ row }) => (
                    <input
                        type="checkbox"
                        checked={selectedIds.has(row.original.id)}
                        onChange={() => toggleSelection(row.original.id)}
                        aria-label={`Select ${row.original.job_title}`}
                    />
                ),
                enableSorting: false,
                size: 40,
            },
            {
                accessorKey: 'job_title',
                header: 'Job Title',
                cell: ({ row }) => (
                    <button
                        className="btn btn--ghost"
                        style={{ padding: 0, textAlign: 'left', fontWeight: 600, color: 'var(--text-primary)' }}
                        onClick={() => openAnalysis(row.original.id)}
                        title={row.original.job_title}
                        aria-label={`View details for ${row.original.job_title}`}
                    >
                        {truncate(row.original.job_title, 45)}
                    </button>
                ),
                size: 280,
            },
            {
                accessorKey: 'company_name',
                header: 'Company',
                cell: ({ getValue }) => (
                    <span style={{ color: 'var(--text-secondary)' }}>{truncate(getValue() as string, 25)}</span>
                ),
                size: 160,
            },
            {
                accessorKey: 'time_posted',
                header: 'Posted',
                cell: ({ getValue }) => {
                    const raw = getValue() as string | null;
                    if (!raw) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
                    const d = new Date(raw);
                    const now = new Date();
                    const diffMs = now.getTime() - d.getTime();
                    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
                    let label: string;
                    if (diffDays === 0) label = 'Today';
                    else if (diffDays === 1) label = '1d ago';
                    else if (diffDays < 7) label = `${diffDays}d ago`;
                    else if (diffDays < 30) label = `${Math.floor(diffDays / 7)}w ago`;
                    else label = `${Math.floor(diffDays / 30)}mo ago`;
                    return (
                        <span
                            style={{
                                color: diffDays <= 3 ? 'var(--color-success)' : diffDays <= 14 ? 'var(--text-secondary)' : 'var(--text-muted)',
                                fontSize: 'var(--fs-xs)',
                                fontFamily: 'var(--font-mono)',
                            }}
                            title={d.toLocaleDateString()}
                        >
                            {label}
                        </span>
                    );
                },
                size: 80,
            },
            {
                id: 'country',
                header: 'Country',
                accessorFn: (row: Job) => {
                    const loc = row.location || '';
                    // Extract last part after comma (usually country or state)
                    const parts = loc.split(',').map((s: string) => s.trim());
                    if (parts.length === 0) return '—';
                    const last = parts[parts.length - 1];
                    // Common mappings
                    if (/brazil/i.test(last)) return '🇧🇷 BR';
                    if (/united states|usa/i.test(last)) return '🇺🇸 US';
                    if (/canada/i.test(last)) return '🇨🇦 CA';
                    if (/united kingdom|uk/i.test(last)) return '🇬🇧 UK';
                    if (/germany|deutschland/i.test(last)) return '🇩🇪 DE';
                    if (/india/i.test(last)) return '🇮🇳 IN';
                    if (/remote/i.test(loc)) return '🌍 Remote';
                    // US state abbreviations (2 uppercase letters)
                    if (/^[A-Z]{2}$/.test(last)) return `🇺🇸 ${last}`;
                    // Brazilian states
                    if (/brazil/i.test(loc)) return '🇧🇷 BR';
                    return truncate(last, 10);
                },
                cell: ({ getValue }) => (
                    <span style={{ fontSize: 'var(--fs-xs)', whiteSpace: 'nowrap' }}>
                        {getValue() as string}
                    </span>
                ),
                size: 85,
            },
            {
                id: 'easy_apply',
                header: '⚡',
                accessorFn: (row: Job) => !!row.apply_url,
                cell: ({ getValue }) => (
                    <span
                        style={{ fontSize: '14px', opacity: getValue() ? 1 : 0.2 }}
                        title={getValue() ? 'Easy Apply available' : 'External application'}
                    >
                        {getValue() ? '✅' : '—'}
                    </span>
                ),
                enableSorting: false,
                size: 45,
            },
            {
                accessorKey: 'score',
                header: 'Score',
                cell: ({ getValue }) => {
                    const { text, className } = formatScore(getValue() as number | null);
                    return <span className={className}>{text}</span>;
                },
                size: 70,
            },
            {
                accessorKey: 'status',
                header: 'Status',
                cell: ({ row }) => (
                    <select
                        className={`badge badge--${row.original.status}`}
                        value={row.original.status}
                        onChange={(e) => handleStatusChange(row.original, e.target.value as JobStatus)}
                        style={{
                            border: 'none',
                            cursor: 'pointer',
                            appearance: 'auto',
                            WebkitAppearance: 'menulist',
                            background: 'transparent',
                        }}
                    >
                        {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>{getStatusLabel(s)}</option>
                        ))}
                    </select>
                ),
                size: 130,
            },
            {
                accessorKey: 'work_type',
                header: 'Work Type',
                cell: ({ getValue }) => (
                    <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-xs)' }}>
                        {(getValue() as string) || '—'}
                    </span>
                ),
                size: 110,
            },
            {
                accessorKey: 'location',
                header: 'Location',
                cell: ({ getValue }) => (
                    <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-xs)' }}>
                        {truncate(getValue() as string, 25)}
                    </span>
                ),
                size: 160,
            },
            {
                accessorKey: 'updated_at',
                header: 'Updated',
                cell: ({ getValue }) => (
                    <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-xs)', fontFamily: 'var(--font-mono)' }}>
                        {formatDate(getValue() as string)}
                    </span>
                ),
                size: 110,
            },
            {
                id: 'actions',
                header: '',
                cell: ({ row }) => (
                    <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                        {row.original.job_url && (
                            <a
                                href={row.original.job_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn--ghost btn--sm"
                                title="View listing"
                                aria-label="Open job listing"
                                style={{ fontSize: '12px' }}
                            >
                                🔗
                            </a>
                        )}
                        <button
                            className="btn btn--ghost btn--sm"
                            onClick={() => setSelectedJobId(row.original.id)}
                            title="View details"
                            aria-label="View job details"
                            style={{ fontSize: '12px' }}
                        >
                            ⟩
                        </button>
                    </div>
                ),
                enableSorting: false,
                size: 80,
            },
        ],
        [selectedIds, selectAll, clearSelection, toggleSelection, setSelectedJobId, openAnalysis, handleStatusChange, response?.data]
    );

    const data = response?.data || [];
    const totalPages = response ? Math.ceil(response.total / limit) : 1;

    const table = useReactTable({
        data,
        columns,
        state: { sorting },
        onSortingChange: handleSortingChange,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        manualPagination: true,
        manualSorting: true,
        pageCount: totalPages,
    });

    // Virtual scrolling
    const tableContainerRef = useRef<HTMLDivElement>(null);
    const { rows } = table.getRowModel();
    const shouldVirtualize = rows.length > VIRTUAL_THRESHOLD;

    const virtualizer = useVirtualizer({
        count: rows.length,
        getScrollElement: () => tableContainerRef.current,
        estimateSize: () => ROW_HEIGHT,
        overscan: 10,
    });

    return (
        <div>
            {/* Toolbar */}
            <div className="toolbar">
                <div className="toolbar__left">
                    <div className="search-input">
                        <span className="search-input__icon">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <circle cx="7" cy="7" r="5.5" /><line x1="11.5" y1="11.5" x2="15" y2="15" />
                            </svg>
                        </span>
                        <input
                            type="text"
                            placeholder="Search jobs, companies…"
                            value={localSearch}
                            onChange={(e) => setLocalSearch(e.target.value)}
                        />
                    </div>

                    {/* Status filter chips */}
                    <div style={{ display: 'flex', gap: 'var(--space-1)', flexWrap: 'wrap' }}>
                        {filters.status.map((s) => (
                            <span key={s} className="filter-chip">
                                {getStatusLabel(s)}
                                <button
                                    className="filter-chip__remove"
                                    onClick={() => setStatusFilter(filters.status.filter((x) => x !== s))}
                                >
                                    ✕
                                </button>
                            </span>
                        ))}
                    </div>
                </div>

                <div className="toolbar__right">
                    {/* Status filter dropdown */}
                    <select
                        className="btn btn--secondary btn--sm"
                        value=""
                        onChange={(e) => {
                            const val = e.target.value as JobStatus;
                            if (val && !filters.status.includes(val)) {
                                setStatusFilter([...filters.status, val]);
                            }
                            e.target.value = '';
                        }}
                    >
                        <option value="">+ Filter Status</option>
                        {STATUS_OPTIONS.filter((s) => !filters.status.includes(s)).map((s) => (
                            <option key={s} value={s}>{getStatusLabel(s)}</option>
                        ))}
                    </select>

                    {selectedIds.size > 0 && (
                        <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--accent-primary)' }}>
                            {selectedIds.size} selected
                        </span>
                    )}

                    {/* Excel Export */}
                    <button
                        className="btn btn--secondary btn--sm"
                        onClick={() => {
                            api.exportJobsToExcel({
                                status: filters.status.length === 1 ? filters.status[0] : undefined,
                                ids: selectedIds.size > 0 ? Array.from(selectedIds) : undefined,
                            });
                        }}
                        title={selectedIds.size > 0 ? `Export ${selectedIds.size} selected jobs` : 'Export all jobs to Excel'}
                    >
                        📊 Export
                    </button>
                </div>
            </div>

            {/* Table */}
            <div
                className="data-table-container"
                ref={tableContainerRef}
                style={shouldVirtualize ? { maxHeight: '70vh', overflowY: 'auto' } : undefined}
            >
                {isLoading ? (
                    <SkeletonTable rows={10} />
                ) : data.length === 0 ? (
                    <div className="empty-state">
                        <svg className="empty-state__illustration" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                            {/* Clipboard */}
                            <rect x="25" y="18" width="60" height="80" rx="6" stroke="#475569" strokeWidth="2" fill="rgba(255,255,255,0.02)" />
                            <rect x="42" y="12" width="26" height="12" rx="4" stroke="#475569" strokeWidth="2" fill="#1e293b" />
                            {/* Lines */}
                            <line x1="38" y1="42" x2="72" y2="42" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
                            <line x1="38" y1="54" x2="68" y2="54" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
                            <line x1="38" y1="66" x2="60" y2="66" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
                            {/* Magnifying glass */}
                            <circle cx="82" cy="82" r="16" stroke="#6366f1" strokeWidth="2.5" fill="rgba(99,102,241,0.08)" />
                            <line x1="94" y1="94" x2="106" y2="106" stroke="#6366f1" strokeWidth="3" strokeLinecap="round" />
                            {/* Question mark */}
                            <text x="82" y="87" textAnchor="middle" fill="#6366f1" fontSize="16" fontWeight="bold">?</text>
                        </svg>
                        <div className="empty-state__title">No jobs found</div>
                        <div className="empty-state__description">
                            Try adjusting your filters or wait for the pipeline to process new listings.
                        </div>
                    </div>
                ) : (
                    <>
                        <table className="data-table">
                            <thead>
                                {table.getHeaderGroups().map((headerGroup) => (
                                    <tr key={headerGroup.id}>
                                        {headerGroup.headers.map((header) => (
                                            <th
                                                key={header.id}
                                                className={header.column.getIsSorted() ? 'data-table th--sorted' : ''}
                                                style={{ width: header.getSize() }}
                                                onClick={header.column.getToggleSortingHandler()}
                                            >
                                                {flexRender(header.column.columnDef.header, header.getContext())}
                                                {header.column.getIsSorted() === 'asc' && ' ↑'}
                                                {header.column.getIsSorted() === 'desc' && ' ↓'}
                                            </th>
                                        ))}
                                    </tr>
                                ))}
                            </thead>
                            {shouldVirtualize ? (
                                <tbody
                                    style={{
                                        height: `${virtualizer.getTotalSize()}px`,
                                        position: 'relative',
                                    }}
                                >
                                    {virtualizer.getVirtualItems().map((virtualRow) => {
                                        const row = rows[virtualRow.index];
                                        const isChecked = selectedIds.has(row.original.id);
                                        const isFocused = selectedJobId === row.original.id;
                                        return (
                                            <tr
                                                key={row.id}
                                                data-index={virtualRow.index}
                                                ref={(node) => virtualizer.measureElement(node)}
                                                className={cn(
                                                    isChecked && 'tr--selected',
                                                    isFocused && 'tr--focused',
                                                )}
                                                onClick={() => openAnalysis(row.original.id)}
                                                style={{
                                                    cursor: 'pointer',
                                                    position: 'absolute',
                                                    top: 0,
                                                    left: 0,
                                                    width: '100%',
                                                    height: `${virtualRow.size}px`,
                                                    transform: `translateY(${virtualRow.start}px)`,
                                                }}
                                            >
                                                {row.getVisibleCells().map((cell) => (
                                                    <td key={cell.id} style={{ width: cell.column.getSize() }}>
                                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                                    </td>
                                                ))}
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            ) : (
                                <tbody>
                                    {rows.map((row) => {
                                        const isChecked = selectedIds.has(row.original.id);
                                        const isFocused = selectedJobId === row.original.id;
                                        return (
                                            <tr
                                                key={row.id}
                                                className={cn(
                                                    isChecked && 'tr--selected',
                                                    isFocused && 'tr--focused',
                                                )}
                                                onClick={() => openAnalysis(row.original.id)}
                                                style={{ cursor: 'pointer' }}
                                            >
                                                {row.getVisibleCells().map((cell) => (
                                                    <td key={cell.id} style={{ width: cell.column.getSize() }}>
                                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                                    </td>
                                                ))}
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            )}
                        </table>

                        {/* Pagination */}
                        <div className="pagination">
                            <span>
                                Showing {((page - 1) * limit) + 1}–{Math.min(page * limit, response?.total || 0)} of {response?.total || 0}
                            </span>
                            <div className="pagination__controls">
                                <button
                                    className="pagination__btn"
                                    disabled={page <= 1}
                                    onClick={() => setPage(page - 1)}
                                    aria-label="Previous page"
                                >
                                    ← Prev
                                </button>
                                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                                    const pageNum = i + 1;
                                    return (
                                        <button
                                            key={pageNum}
                                            className={cn('pagination__btn', pageNum === page && 'pagination__btn--active')}
                                            onClick={() => setPage(pageNum)}
                                            aria-label={`Page ${pageNum}`}
                                            aria-current={pageNum === page ? 'page' : undefined}
                                        >
                                            {pageNum}
                                        </button>
                                    );
                                })}
                                {totalPages > 5 && <span style={{ color: 'var(--text-muted)' }}>…</span>}
                                <button
                                    className="pagination__btn"
                                    disabled={page >= totalPages}
                                    onClick={() => setPage(page + 1)}
                                    aria-label="Next page"
                                >
                                    Next →
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
