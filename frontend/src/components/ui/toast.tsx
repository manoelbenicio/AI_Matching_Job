'use client';

import { useEffect, useRef } from 'react';
import { useUIStore } from '@/stores/app-store';

const ICONS: Record<string, string> = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
};

function ToastItem({ id, type, message, duration }: {
    id: string;
    type: string;
    message: string;
    duration: number;
}) {
    const removeToast = useUIStore((s) => s.removeToast);
    const progressRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (progressRef.current) {
            progressRef.current.style.animationDuration = `${duration}ms`;
        }
    }, [duration]);

    return (
        <div
            className={`toast toast--${type}`}
            role="status"
            aria-live="polite"
        >
            <span className="toast__icon" aria-hidden="true">
                {ICONS[type] || ICONS.info}
            </span>
            <span className="toast__message">{message}</span>
            <button
                className="toast__close"
                onClick={() => removeToast(id)}
                aria-label="Dismiss notification"
            >
                ✕
            </button>
            <div className="toast__progress" ref={progressRef} />
        </div>
    );
}

export function ToastContainer() {
    const toasts = useUIStore((s) => s.toasts);

    if (toasts.length === 0) return null;

    return (
        <div className="toast-container" aria-label="Notifications">
            {toasts.map((toast) => (
                <ToastItem
                    key={toast.id}
                    id={toast.id}
                    type={toast.type}
                    message={toast.message}
                    duration={toast.duration ?? 4000}
                />
            ))}
        </div>
    );
}
