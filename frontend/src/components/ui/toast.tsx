'use client';

import { useEffect, useRef, useState } from 'react';
import { useUIStore } from '@/stores/app-store';
import './toast.css';

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
    const [exiting, setExiting] = useState(false);
    const progressRef = useRef<HTMLDivElement>(null);
    const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

    // Trigger exit animation before removal
    const dismiss = () => {
        if (exiting) return;
        setExiting(true);
        clearTimeout(timerRef.current);
        setTimeout(() => removeToast(id), 300);
    };

    useEffect(() => {
        if (progressRef.current) {
            progressRef.current.style.animationDuration = `${duration}ms`;
        }
        // Auto-dismiss — start exit 300ms before store removal
        timerRef.current = setTimeout(dismiss, duration - 300);
        return () => clearTimeout(timerRef.current);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [duration]);

    return (
        <div
            className={`toast toast--${type} ${exiting ? 'toast--exit' : ''}`}
            role="status"
            aria-live="polite"
        >
            <span className="toast__icon" aria-hidden="true">
                {ICONS[type] || ICONS.info}
            </span>
            <span className="toast__message">{message}</span>
            <button
                className="toast__close"
                onClick={dismiss}
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
