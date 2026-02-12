'use client';

import { useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import { useUIStore } from '@/stores/app-store';
import { useCommandPaletteShortcut } from '@/hooks/use-keyboard';
import type { ViewMode } from '@/lib/types';
import { ThemeToggle } from '@/components/ui/theme-toggle';

import { SettingsModal } from '@/components/settings/settings-modal';
import { CvManagerModal } from '@/components/cv/cv-manager-modal';
import { QuickAddBar } from '@/components/quick-add/quick-add-bar';

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

const GearIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="8" cy="8" r="2.5" />
        <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M2.9 2.9l1.1 1.1M12 12l1.1 1.1M13.1 2.9L12 4M4 12l-1.1 1.1" />
    </svg>
);

const DocIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M9 1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5L9 1z" />
        <polyline points="9,1 9,5 13,5" />
        <line x1="5" y1="8" x2="11" y2="8" />
        <line x1="5" y1="10.5" x2="9" y2="10.5" />
    </svg>
);

const PlusIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="8" y1="3" x2="8" y2="13" />
        <line x1="3" y1="8" x2="13" y2="8" />
    </svg>
);

export function Header() {
    const { viewMode, setViewMode } = useAppStore();
    const { toggleCommandPalette } = useUIStore();

    const [settingsOpen, setSettingsOpen] = useState(false);
    const [cvOpen, setCvOpen] = useState(false);
    const [quickAddOpen, setQuickAddOpen] = useState(false);

    useCommandPaletteShortcut(toggleCommandPalette);

    return (
        <>
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
                    {/* Quick Add (LinkedIn fetch) */}
                    <button
                        className={`btn btn--ghost btn--sm header-action-btn ${quickAddOpen ? 'header-action-btn--active' : ''}`}
                        onClick={() => setQuickAddOpen(!quickAddOpen)}
                        title="Quick Add — paste LinkedIn URL"
                    >
                        <PlusIcon />
                        <span>Quick Add</span>
                    </button>

                    {/* CV Manager */}
                    <button
                        className="btn btn--ghost btn--sm header-action-btn"
                        onClick={() => setCvOpen(true)}
                        title="CV Manager"
                    >
                        <DocIcon />
                        <span>CV</span>
                    </button>

                    {/* AI Scoring — switches to scoring view mode */}
                    <button
                        className={`btn btn--scoring ${viewMode === 'scoring' ? 'btn--scoring--active' : ''}`}
                        onClick={() => setViewMode(viewMode === 'scoring' ? 'table' : 'scoring')}
                        title="Run AI Scoring Pipeline"
                    >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <path d="M8 1l2 3h3l-2.5 3L12 11l-4-2-4 2 1.5-4L3 4h3L8 1z" />
                        </svg>
                        <span>AI Scoring</span>
                    </button>

                    {/* Settings */}
                    <button
                        className="btn btn--ghost btn--sm header-action-btn"
                        onClick={() => setSettingsOpen(true)}
                        title="Settings — API Keys"
                    >
                        <GearIcon />
                    </button>

                    <ThemeToggle />
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

            {/* Quick Add bar below header */}
            <QuickAddBar open={quickAddOpen} onClose={() => setQuickAddOpen(false)} />

            {/* Slide-over panels */}

            <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
            <CvManagerModal open={cvOpen} onClose={() => setCvOpen(false)} />
        </>
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
