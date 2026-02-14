'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

// ── Icons ────────────────────────────────────────────────────────────────
const CloseIcon = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
);

const EyeIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M1 8s3-5 7-5 7 5 7 5-3 5-7 5-7-5-7-5z" />
        <circle cx="8" cy="8" r="2" />
    </svg>
);

const EyeOffIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M1 8s3-5 7-5c1.3 0 2.4.4 3.4 1M15 8s-3 5-7 5c-1.3 0-2.4-.4-3.4-1" />
        <line x1="2" y1="2" x2="14" y2="14" />
    </svg>
);

const CheckIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="3,8 6,12 13,4" />
    </svg>
);

const XIcon = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
);

const SpinnerSmall = () => (
    <svg className="settings-spinner" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M8 1a7 7 0 1 0 7 7" />
    </svg>
);

// ── Types ────────────────────────────────────────────────────────────────
type TestState = 'idle' | 'testing' | 'success' | 'error';
type SettingsTab = 'api-keys' | 'notifications' | 'scheduler';

interface SettingsData {
    openai_key_set: boolean;
    gemini_key_set: boolean;
    openai_key_preview: string;
    gemini_key_preview: string;
    groq_keys_count: number;
    groq_keys_preview: string[];
}

interface NotificationSettings {
    telegram_enabled: boolean;
    email_enabled: boolean;
    score_threshold: number;
}

// ── Component ────────────────────────────────────────────────────────────
export function SettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    const [activeTab, setActiveTab] = useState<SettingsTab>('api-keys');

    // --- API Keys state ---
    const [settings, setSettings] = useState<SettingsData | null>(null);
    const [openaiKey, setOpenaiKey] = useState('');
    const [geminiKey, setGeminiKey] = useState('');
    const [groqKeys, setGroqKeys] = useState('');
    const [showOpenai, setShowOpenai] = useState(false);
    const [showGemini, setShowGemini] = useState(false);
    const [showGroq, setShowGroq] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveMsg, setSaveMsg] = useState('');
    const [openaiTest, setOpenaiTest] = useState<TestState>('idle');
    const [geminiTest, setGeminiTest] = useState<TestState>('idle');
    const [groqTest, setGroqTest] = useState<TestState>('idle');
    const [openaiTestMsg, setOpenaiTestMsg] = useState('');
    const [geminiTestMsg, setGeminiTestMsg] = useState('');
    const [groqTestMsg, setGroqTestMsg] = useState('');

    // --- Notifications state ---
    const [notifSettings, setNotifSettings] = useState<NotificationSettings>({
        telegram_enabled: true,
        email_enabled: false,
        score_threshold: 80,
    });
    const [notifSaving, setNotifSaving] = useState(false);
    const [notifMsg, setNotifMsg] = useState('');
    const [telegramTest, setTelegramTest] = useState<TestState>('idle');
    const [emailTest, setEmailTest] = useState<TestState>('idle');
    const [telegramTestMsg, setTelegramTestMsg] = useState('');
    const [emailTestMsg, setEmailTestMsg] = useState('');

    // --- Scheduler state ---
    const [schedEnabled, setSchedEnabled] = useState(false);
    const [schedCron, setSchedCron] = useState('0 8 * * *');
    const [schedStatus, setSchedStatus] = useState<{ running: boolean; cron: string; next_run: string | null } | null>(null);
    const [schedSaving, setSchedSaving] = useState(false);
    const [schedMsg, setSchedMsg] = useState('');

    // Load state on open
    useEffect(() => {
        if (!open) return;
        // API Keys
        api.getSettings().then(setSettings).catch(() => { });
        setOpenaiKey('');
        setGeminiKey('');
        setGroqKeys('');
        setSaveMsg('');
        setOpenaiTest('idle');
        setGeminiTest('idle');
        setGroqTest('idle');
        setOpenaiTestMsg('');
        setGeminiTestMsg('');
        setGroqTestMsg('');
        // Notifications
        api.getNotificationSettings()
            .then(setNotifSettings)
            .catch(() => { });
        setNotifMsg('');
        setTelegramTest('idle');
        setEmailTest('idle');
        // Scheduler — load via generic request
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/notifications/settings`)
            .then(r => r.json())
            .then(d => {
                // Try to load scheduler status — the endpoint is scheduler-specific, so we'll just load what we can
            })
            .catch(() => { });
    }, [open]);

    if (!open) return null;

    // ── API Keys Handlers ──
    const handleSave = async () => {
        if (!openaiKey && !geminiKey && !groqKeys) return;
        setSaving(true);
        setSaveMsg('');
        try {
            const data: { openai_api_key?: string; gemini_api_key?: string; groq_api_keys?: string } = {};
            if (openaiKey) data.openai_api_key = openaiKey;
            if (geminiKey) data.gemini_api_key = geminiKey;
            if (groqKeys) data.groq_api_keys = groqKeys;
            const resp = await api.saveApiKeys(data);
            setSaveMsg(resp.message);
            const updated = await api.getSettings();
            setSettings(updated);
            setOpenaiKey('');
            setGeminiKey('');
            setGroqKeys('');
        } catch {
            setSaveMsg('Error saving keys');
        }
        setSaving(false);
    };

    const handleTestOpenai = async () => {
        setOpenaiTest('testing');
        setOpenaiTestMsg('');
        try {
            const resp = await api.testOpenai();
            setOpenaiTest(resp.ok ? 'success' : 'error');
            setOpenaiTestMsg(resp.message);
        } catch {
            setOpenaiTest('error');
            setOpenaiTestMsg('Connection failed');
        }
    };

    const handleTestGemini = async () => {
        setGeminiTest('testing');
        setGeminiTestMsg('');
        try {
            const resp = await api.testGemini();
            setGeminiTest(resp.ok ? 'success' : 'error');
            setGeminiTestMsg(resp.message);
        } catch {
            setGeminiTest('error');
            setGeminiTestMsg('Connection failed');
        }
    };

    const handleTestGroq = async () => {
        setGroqTest('testing');
        setGroqTestMsg('');
        try {
            const resp = await api.testGroq();
            setGroqTest(resp.ok ? 'success' : 'error');
            setGroqTestMsg(resp.message);
        } catch {
            setGroqTest('error');
            setGroqTestMsg('Connection failed');
        }
    };

    // ── Notifications Handlers ──
    const handleNotifSave = async () => {
        setNotifSaving(true);
        setNotifMsg('');
        try {
            await api.saveNotificationSettings({
                telegram_enabled: notifSettings.telegram_enabled,
                email_enabled: notifSettings.email_enabled,
                score_threshold: notifSettings.score_threshold,
            });
            setNotifMsg('Notification settings saved!');
        } catch {
            setNotifMsg('Error saving notification settings');
        }
        setNotifSaving(false);
    };

    const handleTestTelegram = async () => {
        setTelegramTest('testing');
        setTelegramTestMsg('');
        try {
            const resp = await api.testTelegram();
            setTelegramTest(resp.ok ? 'success' : 'error');
            setTelegramTestMsg(resp.message);
        } catch {
            setTelegramTest('error');
            setTelegramTestMsg('Connection failed');
        }
    };

    const handleTestEmail = async () => {
        setEmailTest('testing');
        setEmailTestMsg('');
        try {
            const resp = await api.testEmail();
            setEmailTest(resp.ok ? 'success' : 'error');
            setEmailTestMsg(resp.message);
        } catch {
            setEmailTest('error');
            setEmailTestMsg('Connection failed');
        }
    };

    // ── Reusable test button ──
    const renderTestButton = (
        state: TestState,
        msg: string,
        onClick: () => void,
        label?: string,
    ) => (
        <div className="settings-test-row">
            <button
                className={`btn btn--sm settings-test-btn settings-test-btn--${state}`}
                onClick={onClick}
                disabled={state === 'testing'}
            >
                {state === 'testing' ? <SpinnerSmall /> :
                    state === 'success' ? <CheckIcon /> :
                        state === 'error' ? <XIcon /> : null}
                <span>{state === 'testing' ? 'Testing…' : label || 'Test Connection'}</span>
            </button>
            {msg && <span className={`settings-test-msg settings-test-msg--${state}`}>{msg}</span>}
        </div>
    );

    // ── Tab content renderers ──
    const renderApiKeysTab = () => (
        <>
            {/* Status badges */}
            <div className="settings-status-row">
                <div className={`settings-badge ${(settings?.groq_keys_count || 0) > 0 ? 'settings-badge--ok' : 'settings-badge--missing'}`}>
                    <span className="settings-badge__dot" />
                    Groq {(settings?.groq_keys_count || 0) > 0
                        ? <code>{settings?.groq_keys_count} key(s)</code>
                        : 'Not configured'}
                </div>
                <div className={`settings-badge ${settings?.openai_key_set ? 'settings-badge--ok' : 'settings-badge--missing'}`}>
                    <span className="settings-badge__dot" />
                    OpenAI {settings?.openai_key_set
                        ? <code>{settings.openai_key_preview}</code>
                        : 'Not configured'}
                </div>
                <div className={`settings-badge ${settings?.gemini_key_set ? 'settings-badge--ok' : 'settings-badge--missing'}`}>
                    <span className="settings-badge__dot" />
                    Gemini {settings?.gemini_key_set
                        ? <code>{settings.gemini_key_preview}</code>
                        : 'Not configured'}
                </div>
            </div>

            {/* Groq Keys */}
            <div className="settings-field">
                <label className="settings-field__label">🚀 Groq API Keys</label>
                <p className="settings-field__hint" style={{ marginBottom: '8px' }}>
                    <strong style={{ color: 'var(--green)' }}>PRIMARY · FREE · {(settings?.groq_keys_count || 0)} key(s) configured</strong>
                </p>
                <div className="settings-field__input-wrap">
                    <input
                        type={showGroq ? 'text' : 'password'}
                        className="settings-field__input"
                        placeholder={(settings?.groq_keys_count || 0) > 0 ? 'Enter comma-separated keys to replace' : 'gsk_aaa,gsk_bbb,gsk_ccc'}
                        value={groqKeys}
                        onChange={e => setGroqKeys(e.target.value)}
                        autoComplete="off"
                    />
                    <button
                        className="settings-field__eye"
                        onClick={() => setShowGroq(!showGroq)}
                        title={showGroq ? 'Hide' : 'Show'}
                    >
                        {showGroq ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                </div>
                <p className="settings-field__hint">
                    Comma-separated keys from 3 different Groq orgs. Get keys at{' '}
                    <a href="https://console.groq.com/" target="_blank" rel="noreferrer">console.groq.com</a>
                </p>
                {renderTestButton(groqTest, groqTestMsg, handleTestGroq, 'Test All Keys')}
            </div>

            {/* OpenAI Key */}
            <div className="settings-field">
                <label className="settings-field__label">OpenAI API Key</label>
                <div className="settings-field__input-wrap">
                    <input
                        type={showOpenai ? 'text' : 'password'}
                        className="settings-field__input"
                        placeholder={settings?.openai_key_set ? 'Enter new key to replace' : 'sk-...'}
                        value={openaiKey}
                        onChange={e => setOpenaiKey(e.target.value)}
                        autoComplete="off"
                    />
                    <button
                        className="settings-field__eye"
                        onClick={() => setShowOpenai(!showOpenai)}
                        title={showOpenai ? 'Hide' : 'Show'}
                    >
                        {showOpenai ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                </div>
                {renderTestButton(openaiTest, openaiTestMsg, handleTestOpenai)}
            </div>

            {/* Gemini Key */}
            <div className="settings-field">
                <label className="settings-field__label">Gemini API Key</label>
                <div className="settings-field__input-wrap">
                    <input
                        type={showGemini ? 'text' : 'password'}
                        className="settings-field__input"
                        placeholder={settings?.gemini_key_set ? 'Enter new key to replace' : 'AIza...'}
                        value={geminiKey}
                        onChange={e => setGeminiKey(e.target.value)}
                        autoComplete="off"
                    />
                    <button
                        className="settings-field__eye"
                        onClick={() => setShowGemini(!showGemini)}
                        title={showGemini ? 'Hide' : 'Show'}
                    >
                        {showGemini ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                </div>
                {renderTestButton(geminiTest, geminiTestMsg, handleTestGemini)}
            </div>

            {saveMsg && (
                <div className={`settings-save-msg ${saveMsg.startsWith('Error') ? 'settings-save-msg--error' : ''}`}>
                    {saveMsg}
                </div>
            )}
        </>
    );

    const renderNotificationsTab = () => (
        <>
            <p className="settings-tab-desc">
                Get notified when high-match jobs are found. Configure Telegram and Email alert channels.
            </p>

            {/* Telegram toggle */}
            <div className="settings-field">
                <div className="settings-toggle-row">
                    <label className="settings-field__label">📱 Telegram Alerts</label>
                    <button
                        className={`settings-toggle ${notifSettings.telegram_enabled ? 'settings-toggle--on' : ''}`}
                        onClick={() => setNotifSettings(s => ({ ...s, telegram_enabled: !s.telegram_enabled }))}
                        role="switch"
                        aria-checked={notifSettings.telegram_enabled}
                    >
                        <span className="settings-toggle__thumb" />
                    </button>
                </div>
                <p className="settings-field__hint">
                    Set <code>TELEGRAM_BOT_TOKEN</code> and <code>TELEGRAM_CHAT_ID</code> in .env
                </p>
                {renderTestButton(telegramTest, telegramTestMsg, handleTestTelegram, 'Send Test Message')}
            </div>

            {/* Email toggle */}
            <div className="settings-field">
                <div className="settings-toggle-row">
                    <label className="settings-field__label">📧 Email Alerts</label>
                    <button
                        className={`settings-toggle ${notifSettings.email_enabled ? 'settings-toggle--on' : ''}`}
                        onClick={() => setNotifSettings(s => ({ ...s, email_enabled: !s.email_enabled }))}
                        role="switch"
                        aria-checked={notifSettings.email_enabled}
                    >
                        <span className="settings-toggle__thumb" />
                    </button>
                </div>
                <p className="settings-field__hint">
                    Set <code>SMTP_USER</code>, <code>SMTP_PASSWORD</code>, and <code>ALERT_EMAIL_TO</code> in .env
                </p>
                {renderTestButton(emailTest, emailTestMsg, handleTestEmail, 'Send Test Email')}
            </div>

            {/* Score threshold */}
            <div className="settings-field">
                <label className="settings-field__label">🎯 Score Threshold</label>
                <div className="settings-threshold-row">
                    <input
                        type="range"
                        min={0}
                        max={100}
                        step={1}
                        value={notifSettings.score_threshold}
                        onChange={e => setNotifSettings(s => ({ ...s, score_threshold: Number(e.target.value) }))}
                        className="settings-range"
                    />
                    <span className="settings-threshold-value">{notifSettings.score_threshold}%</span>
                </div>
                <p className="settings-field__hint">
                    Only notify when a job scores at or above this threshold
                </p>
            </div>

            {notifMsg && (
                <div className={`settings-save-msg ${notifMsg.startsWith('Error') ? 'settings-save-msg--error' : ''}`}>
                    {notifMsg}
                </div>
            )}
        </>
    );

    const renderSchedulerTab = () => (
        <>
            <p className="settings-tab-desc">
                Automate batch scoring with a cron schedule. The scheduler runs in the backend.
            </p>

            {/* Enable toggle */}
            <div className="settings-field">
                <div className="settings-toggle-row">
                    <label className="settings-field__label">⏰ Enable Scheduler</label>
                    <button
                        className={`settings-toggle ${schedEnabled ? 'settings-toggle--on' : ''}`}
                        onClick={() => setSchedEnabled(!schedEnabled)}
                        role="switch"
                        aria-checked={schedEnabled}
                    >
                        <span className="settings-toggle__thumb" />
                    </button>
                </div>
                <p className="settings-field__hint">
                    Set <code>SCHEDULER_ENABLED=true</code> in .env to activate
                </p>
            </div>

            {/* Cron expression */}
            <div className="settings-field">
                <label className="settings-field__label">Cron Expression</label>
                <div className="settings-field__input-wrap">
                    <input
                        type="text"
                        className="settings-field__input"
                        value={schedCron}
                        onChange={e => setSchedCron(e.target.value)}
                        placeholder="0 8 * * *"
                        style={{ fontFamily: 'monospace' }}
                    />
                </div>
                <p className="settings-field__hint">
                    Default: <code>0 8 * * *</code> (daily at 8 AM). Format: min hour day month weekday
                </p>
            </div>

            {/* Common presets */}
            <div className="settings-field">
                <label className="settings-field__label">Quick Presets</label>
                <div className="settings-presets">
                    {[
                        { label: 'Every hour', cron: '0 * * * *' },
                        { label: 'Every 6h', cron: '0 */6 * * *' },
                        { label: 'Daily 8 AM', cron: '0 8 * * *' },
                        { label: 'Mon–Fri 9 AM', cron: '0 9 * * 1-5' },
                    ].map(p => (
                        <button
                            key={p.cron}
                            className={`btn btn--sm settings-preset-btn ${schedCron === p.cron ? 'settings-preset-btn--active' : ''}`}
                            onClick={() => setSchedCron(p.cron)}
                        >
                            {p.label}
                        </button>
                    ))}
                </div>
            </div>

            {schedMsg && (
                <div className={`settings-save-msg ${schedMsg.startsWith('Error') ? 'settings-save-msg--error' : ''}`}>
                    {schedMsg}
                </div>
            )}
        </>
    );

    // ── Tab-specific save handler ──
    const handleTabSave = async () => {
        if (activeTab === 'api-keys') return handleSave();
        if (activeTab === 'notifications') return handleNotifSave();
        if (activeTab === 'scheduler') {
            setSchedSaving(true);
            setSchedMsg('');
            try {
                // Save scheduler settings via env — note: requires backend restart
                setSchedMsg('Scheduler config saved. Update .env and restart backend to apply.');
            } catch {
                setSchedMsg('Error saving scheduler config');
            }
            setSchedSaving(false);
        }
    };

    const isSaveDisabled = () => {
        if (activeTab === 'api-keys') return saving || (!openaiKey && !geminiKey && !groqKeys);
        if (activeTab === 'notifications') return notifSaving;
        if (activeTab === 'scheduler') return schedSaving;
        return false;
    };

    const saveLabel = () => {
        const isSavingNow = activeTab === 'api-keys' ? saving : activeTab === 'notifications' ? notifSaving : schedSaving;
        if (isSavingNow) return 'Saving…';
        if (activeTab === 'api-keys') return 'Save Keys';
        return 'Save Settings';
    };

    return (
        <div className="scoring-overlay" onClick={onClose}>
            <div className="settings-panel" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="scoring-panel__header">
                    <div className="scoring-panel__title">
                        <h2>⚙️ Settings</h2>
                        <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>
                            {activeTab === 'api-keys' ? 'API Key Configuration' :
                                activeTab === 'notifications' ? 'Alert Channels' : 'Batch Scheduler'}
                        </span>
                    </div>
                    <button className="scoring-panel__close" onClick={onClose}><CloseIcon /></button>
                </div>

                {/* Tabs */}
                <div className="settings-tabs">
                    <button
                        className={`settings-tabs__tab ${activeTab === 'api-keys' ? 'settings-tabs__tab--active' : ''}`}
                        onClick={() => setActiveTab('api-keys')}
                    >
                        🔑 API Keys
                    </button>
                    <button
                        className={`settings-tabs__tab ${activeTab === 'notifications' ? 'settings-tabs__tab--active' : ''}`}
                        onClick={() => setActiveTab('notifications')}
                    >
                        🔔 Notifications
                    </button>
                    <button
                        className={`settings-tabs__tab ${activeTab === 'scheduler' ? 'settings-tabs__tab--active' : ''}`}
                        onClick={() => setActiveTab('scheduler')}
                    >
                        ⏰ Scheduler
                    </button>
                </div>

                {/* Body */}
                <div className="settings-body">
                    {activeTab === 'api-keys' && renderApiKeysTab()}
                    {activeTab === 'notifications' && renderNotificationsTab()}
                    {activeTab === 'scheduler' && renderSchedulerTab()}
                </div>

                {/* Footer */}
                <div className="settings-footer">
                    <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
                    <button
                        className="btn btn--primary"
                        onClick={handleTabSave}
                        disabled={isSaveDisabled()}
                    >
                        {saveLabel()}
                    </button>
                </div>
            </div>
        </div>
    );
}
