'use client';

import { useRef, useCallback, useState, type ReactNode } from 'react';

interface SplitViewProps {
    left: ReactNode;
    right: ReactNode;
    defaultLeftPercent?: number;
    minLeftPercent?: number;
    maxLeftPercent?: number;
}

export function SplitView({
    left,
    right,
    defaultLeftPercent = 55,
    minLeftPercent = 25,
    maxLeftPercent = 75,
}: SplitViewProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [leftPercent, setLeftPercent] = useState(defaultLeftPercent);
    const [isDragging, setIsDragging] = useState(false);

    const handleMouseDown = useCallback(
        (e: React.MouseEvent) => {
            e.preventDefault();
            setIsDragging(true);

            const container = containerRef.current;
            if (!container) return;

            const onMouseMove = (ev: MouseEvent) => {
                const rect = container.getBoundingClientRect();
                const x = ev.clientX - rect.left;
                const pct = (x / rect.width) * 100;
                setLeftPercent(Math.min(maxLeftPercent, Math.max(minLeftPercent, pct)));
            };

            const onMouseUp = () => {
                setIsDragging(false);
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            };

            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        },
        [minLeftPercent, maxLeftPercent]
    );

    return (
        <div className="split-view" ref={containerRef}>
            <div
                className="split-view__panel"
                style={{ flex: `0 0 ${leftPercent}%` }}
            >
                {left}
            </div>
            <div
                className={`split-view__divider ${isDragging ? 'split-view__divider--dragging' : ''}`}
                onMouseDown={handleMouseDown}
            />
            <div
                className="split-view__panel"
                style={{ flex: `1 1 ${100 - leftPercent}%` }}
            >
                {right}
            </div>
        </div>
    );
}
