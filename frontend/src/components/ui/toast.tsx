'use client';

import { useUIStore } from '@/stores/app-store';

export function ToastContainer() {
    const { toasts, removeToast } = useUIStore();

    if (toasts.length === 0) return null;

    return (
        <div className="toast-container" aria-live="polite">
            {toasts.map((toast) => (
                <div key={toast.id} className={`toast toast--${toast.type}`}>
                    <span style={{ flex: 1 }}>{toast.message}</span>
                    <button
                        className="btn btn--ghost btn--icon"
                        onClick={() => removeToast(toast.id)}
                        aria-label="Dismiss"
                        style={{ fontSize: '12px', width: '24px', height: '24px' }}
                    >
                        ✕
                    </button>
                </div>
            ))}
        </div>
    );
}
