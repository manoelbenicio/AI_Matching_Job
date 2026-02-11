'use client';

import { useAuditTrail } from '@/hooks/use-cv';
import type { AuditEvent } from '@/lib/types';
import './audit-tab.css';

export function AuditTab({ jobId }: { jobId: number }) {
    const { data: events, isLoading } = useAuditTrail(jobId);

    if (isLoading) {
        return (
            <div className="audit-tab">
                {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="skeleton" style={{ height: 48, marginBottom: 8, borderRadius: 8 }} />
                ))}
            </div>
        );
    }

    if (!events || events.length === 0) {
        return (
            <div className="audit-tab__empty">
                <div className="audit-tab__empty-icon">📜</div>
                <h3>No activity yet</h3>
                <p>Status changes, CV enhancements, and other events will appear here.</p>
            </div>
        );
    }

    return (
        <div className="audit-tab">
            <div className="audit-tab__list">
                {events.map((event) => (
                    <AuditEventItem key={event.id} event={event} />
                ))}
            </div>
        </div>
    );
}

function AuditEventItem({ event }: { event: AuditEvent }) {
    const actionConfig = getActionConfig(event.action);
    const timeAgo = formatTimeAgo(event.created_at);

    return (
        <div className="audit-event">
            <div className="audit-event__icon" style={{ background: actionConfig.color }}>
                {actionConfig.icon}
            </div>
            <div className="audit-event__content">
                <div className="audit-event__header">
                    <span className="audit-event__action">{actionConfig.label}</span>
                    <span className="audit-event__time" title={new Date(event.created_at).toLocaleString()}>
                        {timeAgo}
                    </span>
                </div>
                {event.field && (
                    <div className="audit-event__detail">
                        <span className="audit-event__field">{event.field}</span>
                        {event.old_value && event.new_value ? (
                            <span className="audit-event__change">
                                <span className="audit-event__old">{event.old_value}</span>
                                <span className="audit-event__arrow">→</span>
                                <span className="audit-event__new">{event.new_value}</span>
                            </span>
                        ) : event.new_value ? (
                            <span className="audit-event__change">
                                <span className="audit-event__new">{event.new_value}</span>
                            </span>
                        ) : null}
                    </div>
                )}
            </div>
        </div>
    );
}

// ── Helpers ──

function getActionConfig(action: string): { icon: string; label: string; color: string } {
    const map: Record<string, { icon: string; label: string; color: string }> = {
        status_change: { icon: '🔄', label: 'Status Changed', color: 'rgba(59,130,246,0.2)' },
        score_change: { icon: '📊', label: 'Score Updated', color: 'rgba(34,197,94,0.2)' },
        cv_enhanced: { icon: '✨', label: 'CV Enhanced', color: 'rgba(168,85,247,0.2)' },
        justification_change: { icon: '💬', label: 'Justification Updated', color: 'rgba(245,158,11,0.2)' },
        resume_url_change: { icon: '📎', label: 'Resume URL Updated', color: 'rgba(100,116,139,0.2)' },
        field_change: { icon: '✏️', label: 'Field Updated', color: 'rgba(100,116,139,0.2)' },
    };
    return map[action] || { icon: '📌', label: action.replace('_', ' '), color: 'rgba(100,116,139,0.2)' };
}

function formatTimeAgo(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}
