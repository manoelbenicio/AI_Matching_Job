'use client';

import React from 'react';
import './error-boundary.css';

interface ErrorBoundaryProps {
    children: React.ReactNode;
    fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
    errorInfo: string;
}

/**
 * React Error Boundary — catches JS errors in child tree.
 * Styled glassmorphism card with retry + copy-error actions.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: '' };
    }

    static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        console.error('[ErrorBoundary] Caught:', error, info.componentStack);
        this.setState({ errorInfo: info.componentStack || '' });
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: '' });
    };

    handleCopyError = async () => {
        const errorText = [
            `Error: ${this.state.error?.message}`,
            `Stack: ${this.state.error?.stack}`,
            `Component: ${this.state.errorInfo}`,
        ].join('\n\n');

        try {
            await navigator.clipboard.writeText(errorText);
        } catch {
            // Fallback for insecure contexts
            const textarea = document.createElement('textarea');
            textarea.value = errorText;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            const isNetworkError = this.state.error?.message?.toLowerCase().includes('fetch') ||
                this.state.error?.message?.toLowerCase().includes('network') ||
                this.state.error?.message?.toLowerCase().includes('timeout');

            return (
                <div className="error-boundary">
                    <div className="error-boundary__card">
                        <div className="error-boundary__icon-wrap">
                            <span className="error-boundary__icon" aria-hidden="true">
                                {isNetworkError ? '📡' : '⚠️'}
                            </span>
                        </div>

                        <h2 className="error-boundary__title">
                            {isNetworkError ? 'Connection Lost' : 'Something went wrong'}
                        </h2>

                        <p className="error-boundary__message">
                            {isNetworkError
                                ? 'Unable to reach the server. Check your connection and try again.'
                                : this.state.error?.message || 'An unexpected error occurred.'}
                        </p>

                        {!isNetworkError && this.state.error?.message && (
                            <pre className="error-boundary__stack">
                                {this.state.error.message}
                            </pre>
                        )}

                        <div className="error-boundary__actions">
                            <button
                                className="error-boundary__retry"
                                onClick={this.handleRetry}
                            >
                                <span aria-hidden="true">↻</span> Try Again
                            </button>
                            <button
                                className="error-boundary__copy"
                                onClick={this.handleCopyError}
                            >
                                <span aria-hidden="true">📋</span> Copy Error
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
