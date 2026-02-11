'use client';

import { Header } from '@/components/layout/header';
import { MetricsBar } from '@/components/layout/metrics-bar';
import { ToastContainer } from '@/components/ui/toast';
import { CommandPalette } from '@/components/ui/command-palette';
import { SplitView } from '@/components/ui/split-view';
import { DataTable } from '@/components/data-table/data-table';
import { KanbanBoard } from '@/components/kanban/kanban-board';
import { JobDetailPanel } from '@/components/detail-panel/job-detail-panel';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { useAppStore } from '@/stores/app-store';
import { useKeyboardNav } from '@/hooks/use-keyboard-nav';

export default function Home() {
  const viewMode = useAppStore((s) => s.viewMode);
  useKeyboardNav();

  return (
    <div className="app-shell">
      <Header />

      <main className="main-content">
        <MetricsBar />

        <ErrorBoundary>
          {viewMode === 'table' && <DataTable />}
          {viewMode === 'kanban' && <KanbanBoard />}
          {viewMode === 'split' && (
            <SplitView
              left={<DataTable />}
              right={<KanbanBoard />}
              defaultLeftPercent={55}
              minLeftPercent={25}
              maxLeftPercent={75}
            />
          )}
        </ErrorBoundary>
      </main>

      <JobDetailPanel />
      <CommandPalette />
      <ToastContainer />
    </div>
  );
}
