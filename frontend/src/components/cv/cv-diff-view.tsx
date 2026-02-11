'use client';

import type { DiffChunk } from '@/lib/types';

interface CvDiffViewProps {
    diff: DiffChunk[];
}

export function CvDiffView({ diff }: CvDiffViewProps) {
    if (diff.length === 0) return null;

    return (
        <div className="cv-diff">
            <h5 className="cv-diff__title">Changes</h5>
            <div className="cv-diff__container">
                {diff.map((chunk, i) => (
                    <div key={i} className={`cv-diff__line cv-diff__line--${chunk.type}`}>
                        <span className="cv-diff__marker">
                            {chunk.type === 'added' ? '+' : chunk.type === 'removed' ? '−' : ' '}
                        </span>
                        <span className="cv-diff__content">{chunk.content}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
