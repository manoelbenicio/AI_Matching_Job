'use client';

import { useAppStore } from '@/stores/app-store';
import { useUIStore } from '@/stores/app-store';
import { useCommandPaletteShortcut } from '@/hooks/use-keyboard';
import type { ViewMode } from '@/lib/types';

// === SVG Icons (inline to avoid external deps) ===
const TableIcon = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="14" height="14" rx="2" />
        <line x1="1" y1="5.5" x2="15" y2="5.5" />
        <line x1="1" y1="10" x2="15" y2="10" />
        <line x1="5.5" y1="5.5" x2="5.5" y2="15" />
    </svg>
);

const KanbanIcon = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="4" height="14" rx="1" />
        <rect x="6" y="1" width="4" height="10" rx="1" />
        <rect x="11" y="1" width="4" height="7" rx="1" />
    </svg>
);

const SplitIcon = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="14" height="14" rx="2" />
        <line x1="8" y1="1" x2="8" y2="15" />
    </svg>
);

const SearchIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="7" cy="7" r="5.5" />
        <line x1="11.5" y1="11.5" x2="15" y2="15" />
    </svg>
);

export function Header() {
    const { viewMode, setViewMode } = useAppStore();
    const { toggleCommandPalette } = useUIStore();

    useCommandPaletteShortcut(toggleCommandPalette);

    return (
        <header className="app-header">
            <div className="app-header__brand">
                <h1 className="app-header__logo">
                    <span className="app-header__logo-accent">AI</span> Job Matcher
                </h1>
                <span className="live-dot" title="Connected" />
            </div>

            <div className="app-header__nav">
                <ViewSwitcher current={viewMode} onChange={setViewMode} />
            </div>

            <div className="app-header__actions">
                <button
                    className="btn btn--ghost btn--sm"
                    onClick={toggleCommandPalette}
                    title="Command Palette (Ctrl+K)"
                >
                    <SearchIcon />
                    <span>Search…</span>
                    <kbd className="kbd">⌘K</kbd>
                </button>
            </div>
        </header>
    );
}

function ViewSwitcher({ current, onChange }: { current: ViewMode; onChange: (m: ViewMode) => void }) {
    const views: { mode: ViewMode; icon: React.ReactNode; label: string }[] = [
        { mode: 'table', icon: <TableIcon />, label: 'Table' },
        { mode: 'kanban', icon: <KanbanIcon />, label: 'Kanban' },
        { mode: 'split', icon: <SplitIcon />, label: 'Split' },
    ];

    return (
        <div className="view-switcher" role="tablist" aria-label="View mode">
            {views.map(({ mode, icon, label }) => (
                <button
                    key={mode}
                    role="tab"
                    aria-selected={current === mode}
                    className={`view-switcher__btn ${current === mode ? 'view-switcher__btn--active' : ''}`}
                    onClick={() => onChange(mode)}
                >
                    {icon}
                    <span>{label}</span>
                </button>
            ))}
        </div>
    );
}
