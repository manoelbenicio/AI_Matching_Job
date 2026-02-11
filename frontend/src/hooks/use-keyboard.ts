'use client';

import { useEffect, useCallback } from 'react';

type KeyCombo = {
    key: string;
    ctrl?: boolean;
    meta?: boolean;
    shift?: boolean;
    alt?: boolean;
};

type ShortcutHandler = (e: KeyboardEvent) => void;
type ShortcutDef = { combo: KeyCombo; handler: ShortcutHandler; description: string };

/**
 * Register global keyboard shortcuts.
 */
export function useKeyboardShortcuts(shortcuts: ShortcutDef[]) {
    const handleKeyDown = useCallback(
        (e: KeyboardEvent) => {
            // Don't fire in inputs/textareas
            const target = e.target as HTMLElement;
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;
            if (target.isContentEditable) return;

            for (const { combo, handler } of shortcuts) {
                const modMatch =
                    (combo.ctrl ? e.ctrlKey : true) &&
                    (combo.meta ? e.metaKey : true) &&
                    (combo.shift ? e.shiftKey : true) &&
                    (combo.alt ? e.altKey : true);

                if (modMatch && e.key.toLowerCase() === combo.key.toLowerCase()) {
                    e.preventDefault();
                    handler(e);
                    return;
                }
            }
        },
        [shortcuts]
    );

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);
}

/**
 * Register Cmd/Ctrl+K for command palette.
 */
export function useCommandPaletteShortcut(toggle: () => void) {
    useKeyboardShortcuts([
        {
            combo: { key: 'k', ctrl: true },
            handler: () => toggle(),
            description: 'Toggle command palette',
        },
        {
            combo: { key: 'k', meta: true },
            handler: () => toggle(),
            description: 'Toggle command palette (Mac)',
        },
    ]);
}
