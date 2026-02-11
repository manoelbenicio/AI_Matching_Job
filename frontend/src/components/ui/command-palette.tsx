'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useUIStore, useAppStore } from '@/stores/app-store';
import { useJobs } from '@/hooks/use-jobs';
import type { Job, ViewMode, JobStatus } from '@/lib/types';

// ─── Icons ──────────────────────────────────────────────────────
const SearchIcon = () => (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="7" cy="7" r="5.5" />
        <line x1="11.5" y1="11.5" x2="15" y2="15" />
    </svg>
);

const TableIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="14" height="14" rx="2" />
        <line x1="1" y1="5.5" x2="15" y2="5.5" />
        <line x1="5.5" y1="5.5" x2="5.5" y2="15" />
    </svg>
);

const KanbanIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="4" height="14" rx="1" />
        <rect x="6" y="1" width="4" height="10" rx="1" />
        <rect x="11" y="1" width="4" height="7" rx="1" />
    </svg>
);

const SplitIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="14" height="14" rx="2" />
        <line x1="8" y1="1" x2="8" y2="15" />
    </svg>
);

const FilterIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M1 3h14M3 8h10M5 13h6" strokeLinecap="round" />
    </svg>
);

const ClearIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="8" cy="8" r="6.5" />
        <line x1="5.5" y1="5.5" x2="10.5" y2="10.5" />
        <line x1="10.5" y1="5.5" x2="5.5" y2="10.5" />
    </svg>
);

const JobIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="2" y="4" width="12" height="10" rx="1.5" />
        <path d="M5 4V2.5A1.5 1.5 0 016.5 1h3A1.5 1.5 0 0111 2.5V4" />
    </svg>
);

// ─── Types ──────────────────────────────────────────────────────
interface CommandItem {
    id: string;
    label: string;
    group: string;
    icon: React.ReactNode;
    shortcut?: string;
    keywords?: string[];
    onSelect: () => void;
}

// ─── Simple fuzzy match ─────────────────────────────────────────
function fuzzyMatch(text: string, query: string): boolean {
    const lower = text.toLowerCase();
    const q = query.toLowerCase();
    let qi = 0;
    for (let i = 0; i < lower.length && qi < q.length; i++) {
        if (lower[i] === q[qi]) qi++;
    }
    return qi === q.length;
}

function scoreMatch(text: string, query: string): number {
    const lower = text.toLowerCase();
    const q = query.toLowerCase();
    // Exact prefix gets highest score
    if (lower.startsWith(q)) return 100;
    // Contains gets high score
    if (lower.includes(q)) return 80;
    // Fuzzy match gets lower score
    if (fuzzyMatch(lower, q)) return 50;
    return 0;
}

// ─── Component ──────────────────────────────────────────────────
export function CommandPalette() {
    const { commandPaletteOpen, setCommandPaletteOpen } = useUIStore();
    const { setViewMode, setSearch, setStatusFilter, clearFilters, setSelectedJobId } = useAppStore();
    const { data: jobsData } = useJobs();

    const [query, setQuery] = useState('');
    const [activeIndex, setActiveIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);
    const listRef = useRef<HTMLDivElement>(null);

    // ── Build command list ──────────────────────────────────────
    const staticCommands: CommandItem[] = useMemo(() => [
        // View commands
        {
            id: 'view-table',
            label: 'Switch to Table View',
            group: 'Views',
            icon: <TableIcon />,
            shortcut: '⌘1',
            keywords: ['table', 'grid', 'list', 'view'],
            onSelect: () => setViewMode('table' as ViewMode),
        },
        {
            id: 'view-kanban',
            label: 'Switch to Kanban View',
            group: 'Views',
            icon: <KanbanIcon />,
            shortcut: '⌘2',
            keywords: ['kanban', 'board', 'pipeline', 'view'],
            onSelect: () => setViewMode('kanban' as ViewMode),
        },
        {
            id: 'view-split',
            label: 'Switch to Split View',
            group: 'Views',
            icon: <SplitIcon />,
            shortcut: '⌘3',
            keywords: ['split', 'dual', 'side', 'view'],
            onSelect: () => setViewMode('split' as ViewMode),
        },
        // Filter commands
        {
            id: 'filter-qualified',
            label: 'Show Qualified Jobs',
            group: 'Filters',
            icon: <FilterIcon />,
            keywords: ['filter', 'qualified', 'status'],
            onSelect: () => setStatusFilter(['qualified']),
        },
        {
            id: 'filter-enhanced',
            label: 'Show Enhanced Jobs',
            group: 'Filters',
            icon: <FilterIcon />,
            keywords: ['filter', 'enhanced', 'status'],
            onSelect: () => setStatusFilter(['enhanced']),
        },
        {
            id: 'filter-pending',
            label: 'Show Pending Jobs',
            group: 'Filters',
            icon: <FilterIcon />,
            keywords: ['filter', 'pending', 'status'],
            onSelect: () => setStatusFilter(['pending']),
        },
        {
            id: 'filter-errors',
            label: 'Show Error Jobs',
            group: 'Filters',
            icon: <FilterIcon />,
            keywords: ['filter', 'error', 'status', 'failed'],
            onSelect: () => setStatusFilter(['error']),
        },
        {
            id: 'filter-clear',
            label: 'Clear All Filters',
            group: 'Filters',
            icon: <ClearIcon />,
            keywords: ['clear', 'reset', 'filter', 'all'],
            onSelect: () => clearFilters(),
        },
    ], [setViewMode, setStatusFilter, clearFilters]);

    // ── Job result commands (from current data) ─────────────────
    const jobCommands: CommandItem[] = useMemo(() => {
        if (!jobsData?.data || !query) return [];
        return jobsData.data
            .filter((job: Job) => {
                const searchText = `${job.job_title} ${job.company_name} ${job.location || ''}`;
                return scoreMatch(searchText, query) > 0;
            })
            .slice(0, 8)
            .map((job: Job) => ({
                id: `job-${job.id}`,
                label: job.job_title,
                group: 'Jobs',
                icon: <JobIcon />,
                keywords: [job.company_name, job.location || ''].filter(Boolean) as string[],
                onSelect: () => setSelectedJobId(job.id),
            }));
    }, [jobsData?.data, query, setSelectedJobId]);

    // ── Filtered + sorted results ───────────────────────────────
    const filteredCommands = useMemo(() => {
        const all = [...staticCommands, ...jobCommands];
        if (!query.trim()) return staticCommands; // Show only static when no query

        return all
            .map((cmd) => {
                const labelScore = scoreMatch(cmd.label, query);
                const keywordScore = cmd.keywords
                    ? Math.max(...cmd.keywords.map((k) => scoreMatch(k, query)), 0)
                    : 0;
                return { cmd, score: Math.max(labelScore, keywordScore) };
            })
            .filter(({ score }) => score > 0)
            .sort((a, b) => b.score - a.score)
            .map(({ cmd }) => cmd);
    }, [staticCommands, jobCommands, query]);

    // ── Group results ───────────────────────────────────────────
    const grouped = useMemo(() => {
        const groups = new Map<string, CommandItem[]>();
        for (const cmd of filteredCommands) {
            if (!groups.has(cmd.group)) groups.set(cmd.group, []);
            groups.get(cmd.group)!.push(cmd);
        }
        return groups;
    }, [filteredCommands]);

    // ── Side effects ────────────────────────────────────────────
    useEffect(() => {
        if (commandPaletteOpen) {
            setQuery('');
            setActiveIndex(0);
            // Focus after animation frame
            requestAnimationFrame(() => inputRef.current?.focus());
        }
    }, [commandPaletteOpen]);

    useEffect(() => {
        setActiveIndex(0);
    }, [query]);

    // Keep active item scrolled into view
    useEffect(() => {
        const list = listRef.current;
        if (!list) return;
        const active = list.querySelector('[data-active="true"]') as HTMLElement;
        if (active) {
            active.scrollIntoView({ block: 'nearest' });
        }
    }, [activeIndex]);

    // ── Keyboard navigation ─────────────────────────────────────
    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            const count = filteredCommands.length;
            if (!count) return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    setActiveIndex((prev) => (prev + 1) % count);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    setActiveIndex((prev) => (prev - 1 + count) % count);
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (filteredCommands[activeIndex]) {
                        filteredCommands[activeIndex].onSelect();
                        setCommandPaletteOpen(false);
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    setCommandPaletteOpen(false);
                    break;
            }
        },
        [filteredCommands, activeIndex, setCommandPaletteOpen]
    );

    const handleSelect = useCallback(
        (cmd: CommandItem) => {
            cmd.onSelect();
            setCommandPaletteOpen(false);
        },
        [setCommandPaletteOpen]
    );

    // ── Render ──────────────────────────────────────────────────
    if (!commandPaletteOpen) return null;

    let flatIndex = 0;

    return (
        <>
            {/* Backdrop */}
            <div
                className="cmd-backdrop"
                onClick={() => setCommandPaletteOpen(false)}
                aria-hidden
            />

            {/* Palette */}
            <div
                className="cmd-palette"
                role="dialog"
                aria-modal="true"
                aria-label="Command palette"
                onKeyDown={handleKeyDown}
            >
                {/* Search input */}
                <div className="cmd-palette__header">
                    <SearchIcon />
                    <input
                        ref={inputRef}
                        className="cmd-palette__input"
                        placeholder="Search commands, jobs, or actions…"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        autoComplete="off"
                        spellCheck={false}
                    />
                    <kbd className="kbd">ESC</kbd>
                </div>

                {/* Results list */}
                <div className="cmd-palette__body" ref={listRef}>
                    {filteredCommands.length === 0 ? (
                        <div className="cmd-palette__empty">
                            <span>No results for &ldquo;{query}&rdquo;</span>
                        </div>
                    ) : (
                        Array.from(grouped.entries()).map(([group, items]) => (
                            <div key={group} className="cmd-group">
                                <div className="cmd-group__label">{group}</div>
                                {items.map((cmd) => {
                                    const idx = flatIndex++;
                                    return (
                                        <button
                                            key={cmd.id}
                                            className={`cmd-item ${idx === activeIndex ? 'cmd-item--active' : ''}`}
                                            data-active={idx === activeIndex}
                                            onClick={() => handleSelect(cmd)}
                                            onMouseEnter={() => setActiveIndex(idx)}
                                            role="option"
                                            aria-selected={idx === activeIndex}
                                        >
                                            <span className="cmd-item__icon">{cmd.icon}</span>
                                            <span className="cmd-item__label">{cmd.label}</span>
                                            {cmd.keywords && cmd.group === 'Jobs' && (
                                                <span className="cmd-item__meta">{cmd.keywords[0]}</span>
                                            )}
                                            {cmd.shortcut && (
                                                <kbd className="cmd-item__shortcut">{cmd.shortcut}</kbd>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        ))
                    )}
                </div>

                {/* Footer hints */}
                <div className="cmd-palette__footer">
                    <span><kbd className="kbd kbd--sm">↑↓</kbd> Navigate</span>
                    <span><kbd className="kbd kbd--sm">↵</kbd> Select</span>
                    <span><kbd className="kbd kbd--sm">Esc</kbd> Close</span>
                </div>
            </div>
        </>
    );
}
